import 'dart:async';
import 'package:flutter/material.dart';
import '../api.dart';
import '../theme.dart';
import '../widgets/message_bubble.dart';
import '../widgets/typing_indicator.dart';
import '../services/sync_service.dart';
import 'memory_screen.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<ChatMessage> _messages = [];
  final TextEditingController _ctrl = TextEditingController();
  final ScrollController _scroll = ScrollController();
  int _pendingCount = 0;
  bool _sessionActive = false;
  bool _isOnline = true;
  StreamSubscription<bool>? _connectivitySub;

  bool get _loading => _pendingCount > 0;

  @override
  void initState() {
    super.initState();

    _isOnline = SyncService().isOnline;

    // Escuchar cambios de conectividad
    _connectivitySub = SyncService().onlineStream.listen((online) {
      if (mounted) setState(() => _isOnline = online);
      if (online && _hasPendingMessages()) {
        _showSyncSnackbar();
      }
    });

    // Cuando un mensaje offline recibe respuesta, actualizar la UI
    SyncService().onMessageSynced = (localId, response) {
      if (!mounted) return;
      setState(() {
        // Buscar el placeholder de respuesta asociado al mensaje pendiente
        final responseId = 'resp_$localId';
        final idx = _messages.indexWhere((m) => m.id == responseId);
        if (idx != -1) {
          _messages[idx] = _messages[idx].copyWith(
            content: response,
            isTyping: false,
            device: kDevice,
          );
        }
        // Marcar el mensaje de usuario como ya no pendiente
        final userIdx = _messages.indexWhere((m) => m.id == localId);
        if (userIdx != -1) {
          _messages[userIdx] = _messages[userIdx].copyWith(pending: false);
        }
      });
      Future.delayed(const Duration(milliseconds: 100), _scrollToBottom);
    };

    _addMessage(ChatMessage(
      id: '0',
      role: 'assistant',
      content: 'Buenos días. Soy SARA, su asistente con memoria persistente. ¿En qué puedo asistirle hoy?',
      device: 'system',
      time: DateTime.now(),
    ));
  }

  @override
  void dispose() {
    _connectivitySub?.cancel();
    SyncService().onMessageSynced = null;
    _ctrl.dispose();
    _scroll.dispose();
    super.dispose();
  }

  bool _hasPendingMessages() => _messages.any((m) => m.pending);

  void _showSyncSnackbar() {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text('Conexión restaurada. Sincronizando mensajes...'),
        backgroundColor: const Color(0xFF455A64),
        duration: const Duration(seconds: 3),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  void _addMessage(ChatMessage msg) {
    setState(() => _messages.add(msg));
    Future.delayed(const Duration(milliseconds: 100), _scrollToBottom);
  }

  void _scrollToBottom() {
    if (_scroll.hasClients) {
      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  Future<void> _send() async {
    final text = _ctrl.text.trim();
    if (text.isEmpty || _loading) return;

    final localId = DateTime.now().millisecondsSinceEpoch.toString();

    setState(() {
      _sessionActive = true;
      _pendingCount++;
    });

    _addMessage(ChatMessage(
      id: localId,
      role: 'user',
      content: text,
      device: kDevice,
      time: DateTime.now(),
      pending: !_isOnline,
    ));
    _ctrl.clear();

    final responseId = 'resp_$localId';
    _addMessage(ChatMessage(
      id: responseId,
      role: 'assistant',
      content: '',
      device: 'system',
      time: DateTime.now(),
      isTyping: true,
    ));

    try {
      final response = await SyncService().sendOrQueue(localId, text);

      setState(() {
        final idx = _messages.indexWhere((m) => m.id == responseId);
        if (idx != -1) {
          if (response != null) {
            // Respuesta inmediata (online)
            _messages[idx] = _messages[idx].copyWith(
              content: response,
              isTyping: false,
              device: kDevice,
            );
          } else {
            // Sin conexión: reemplazar typing por placeholder
            _messages[idx] = _messages[idx].copyWith(
              content: 'Mensaje en cola. Se enviará cuando haya conexión.',
              isTyping: false,
              device: 'system',
            );
          }
        }
      });
      Future.delayed(const Duration(milliseconds: 100), _scrollToBottom);
    } catch (e) {
      setState(() {
        final idx = _messages.indexWhere((m) => m.id == responseId);
        if (idx != -1) {
          _messages[idx] = _messages[idx].copyWith(
            content: 'Error al conectar con el servidor.',
            isTyping: false,
          );
        }
      });
    } finally {
      setState(() => _pendingCount = (_pendingCount - 1).clamp(0, 99));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SaraColors.neutral,
      appBar: AppBar(
        backgroundColor: const Color(0xFF141618),
        title: Row(
          children: [
            Container(
              width: 32, height: 32,
              decoration: BoxDecoration(
                color: SaraColors.surface,
                shape: BoxShape.circle,
                border: Border.all(color: SaraColors.secondary, width: 1),
              ),
              child: const Center(
                child: Text('S', style: TextStyle(
                  color: SaraColors.tertiary, fontSize: 13, fontWeight: FontWeight.bold,
                )),
              ),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('SARA', style: TextStyle(
                  color: SaraColors.primary, fontSize: 15, fontWeight: FontWeight.w600,
                )),
                Row(
                  children: [
                    Container(
                      width: 5, height: 5,
                      decoration: BoxDecoration(
                        color: _isOnline
                            ? (_sessionActive ? const Color(0xFF4CAF50) : SaraColors.dim)
                            : const Color(0xFFFF7043),
                        shape: BoxShape.circle,
                        boxShadow: _sessionActive && _isOnline ? [
                          BoxShadow(color: const Color(0xFF4CAF50).withOpacity(0.5), blurRadius: 4),
                        ] : null,
                      ),
                    ),
                    const SizedBox(width: 5),
                    Text(
                      _isOnline
                          ? (_sessionActive ? 'ACTIVE · mobile' : 'EN ESPERA · mobile')
                          : 'SIN CONEXIÓN · cola activa',
                      style: const TextStyle(
                        color: SaraColors.secondary, fontSize: 9,
                        letterSpacing: 0.8, fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.psychology_outlined, size: 20),
            color: SaraColors.secondary,
            onPressed: () => Navigator.push(
              context, MaterialPageRoute(builder: (_) => const MemoryScreen()),
            ),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: const Color(0x0DFFFFFF)),
        ),
      ),
      body: Column(
        children: [
          // Banner de sin conexión
          AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            height: _isOnline ? 0 : 32,
            color: const Color(0xFFBF360C),
            child: _isOnline
                ? null
                : const Center(
                    child: Text(
                      'SIN CONEXIÓN — Los mensajes se sincronizarán al reconectar',
                      style: TextStyle(
                        color: Colors.white, fontSize: 10, letterSpacing: 0.5,
                      ),
                    ),
                  ),
          ),

          // Lista de mensajes
          Expanded(
            child: ListView.builder(
              controller: _scroll,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
              itemCount: _messages.length + 1,
              itemBuilder: (ctx, i) {
                if (i == 0) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 20),
                    child: Center(
                      child: Text(
                        _dateLabel(),
                        style: const TextStyle(
                          color: SaraColors.dim, fontSize: 10,
                          letterSpacing: 1.5, fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  );
                }
                final msg = _messages[i - 1];
                if (msg.isTyping) return const TypingIndicator();
                return MessageBubble(message: msg);
              },
            ),
          ),

          // Input
          Container(
            decoration: const BoxDecoration(
              color: Color(0xFF161819),
              border: Border(top: BorderSide(color: Color(0x0DFFFFFF))),
            ),
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: Container(
                    decoration: BoxDecoration(
                      color: SaraColors.surface,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: const Color(0x0FFFFFFF)),
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                    child: TextField(
                      controller: _ctrl,
                      style: const TextStyle(color: SaraColors.primary, fontSize: 14),
                      maxLines: null,
                      textCapitalization: TextCapitalization.sentences,
                      decoration: InputDecoration(
                        hintText: _isOnline
                            ? 'Escribe tus pensamientos...'
                            : 'Sin conexión — el mensaje se enviará después',
                        hintStyle: const TextStyle(color: SaraColors.dim, fontSize: 14),
                        border: InputBorder.none,
                      ),
                      onSubmitted: (_) => _send(),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                GestureDetector(
                  onTap: _send,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    width: 46, height: 46,
                    decoration: BoxDecoration(
                      color: _ctrl.text.isNotEmpty && !_loading
                          ? (_isOnline ? SaraColors.secondary : const Color(0xFF546E7A))
                          : SaraColors.surface,
                      borderRadius: BorderRadius.circular(13),
                      border: Border.all(color: const Color(0x0FFFFFFF)),
                    ),
                    child: Icon(
                      _isOnline ? Icons.send_rounded : Icons.schedule_send_rounded,
                      size: 18,
                      color: _ctrl.text.isNotEmpty && !_loading
                          ? SaraColors.primary
                          : SaraColors.dim,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _dateLabel() {
    final now = DateTime.now();
    return '${_weekday(now.weekday)}, ${now.day} de ${_month(now.month)}'.toUpperCase();
  }

  String _weekday(int d) => ['','LUNES','MARTES','MIÉRCOLES','JUEVES','VIERNES','SÁBADO','DOMINGO'][d];
  String _month(int m) => ['','enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'][m];
}
