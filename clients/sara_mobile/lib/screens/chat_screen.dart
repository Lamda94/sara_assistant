import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:audioplayers/audioplayers.dart';
import '../api.dart';
import '../monitoring/monitoring_setup_screen.dart';
import 'betting_screen.dart';
import '../theme.dart';
import '../widgets/message_bubble.dart';
import '../widgets/typing_indicator.dart';
import '../services/sync_service.dart';
import '../services/auth_service.dart';
import 'login_screen.dart';
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
  final SpeechToText _stt = SpeechToText();
  final FlutterTts _tts = FlutterTts();
  final AudioPlayer _player = AudioPlayer();
  int _pendingCount = 0;
  bool _sessionActive = false;
  bool _isOnline = true;
  bool _isListening = false;
  bool _sttAvailable = false;
  bool _voiceEnabled = true;
  StreamSubscription<bool>? _connectivitySub;

  bool get _loading => _pendingCount > 0;

  @override
  void initState() {
    super.initState();

    _initVoice();
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

  Future<void> _initVoice() async {
    _sttAvailable = await _stt.initialize(
      onError: (_) => setState(() => _isListening = false),
      onStatus: (status) {
        if (status == 'done' || status == 'notListening') {
          setState(() => _isListening = false);
        }
      },
    );
    await _tts.setLanguage('es-CO');
    await _tts.setSpeechRate(0.5);
    await _tts.setPitch(1.0);
    if (mounted) setState(() {});
  }

  Future<void> _toggleListen() async {
    if (!_sttAvailable) return;
    if (_isListening) {
      await _stt.stop();
      setState(() => _isListening = false);
    } else {
      await _tts.stop();
      setState(() => _isListening = true);
      await _stt.listen(
        localeId: 'es_CO',
        listenFor: const Duration(seconds: 20),
        pauseFor: const Duration(seconds: 3),
        onResult: (result) {
          if (result.finalResult && result.recognizedWords.isNotEmpty) {
            _ctrl.text = result.recognizedWords;
            setState(() => _isListening = false);
            _send();
          }
        },
      );
    }
  }

  Future<void> _speak(String text) async {
    if (!_voiceEnabled) return;
    await _player.stop();
    try {
      final uri = Uri.parse('$kBaseUrl/voice/tts').replace(queryParameters: {
        'text': text,
        'voice': 'es-ES-ElviraNeural',
        'rate': '+0%',
        'pitch': '-5Hz',
      });
      final res = await http.get(uri, headers: {'X-API-Key': kApiKey})
          .timeout(const Duration(seconds: 20));
      if (res.statusCode != 200) throw Exception('TTS ${res.statusCode}');
      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/sara_tts.mp3');
      await file.writeAsBytes(res.bodyBytes);
      await _player.play(DeviceFileSource(file.path));
    } catch (_) {
      // Fallback al TTS nativo si el backend no está disponible
      await _tts.stop();
      await _tts.speak(text);
    }
  }

  @override
  void dispose() {
    _connectivitySub?.cancel();
    SyncService().onMessageSynced = null;
    _stt.stop();
    _tts.stop();
    _player.dispose();
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
      final token = await AuthService().getValidToken();
      final response = await SyncService().sendOrQueue(localId, text,
          googleAccessToken: token);

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
            _speak(response);
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
            icon: Icon(
              _voiceEnabled ? Icons.volume_up_outlined : Icons.volume_off_outlined,
              size: 20,
            ),
            color: _voiceEnabled ? SaraColors.secondary : SaraColors.dim,
            tooltip: _voiceEnabled ? 'Silenciar voz' : 'Activar voz',
            onPressed: () {
              setState(() => _voiceEnabled = !_voiceEnabled);
              if (!_voiceEnabled) { _player.stop(); _tts.stop(); }
            },
          ),
          IconButton(
            icon: const Icon(Icons.psychology_outlined, size: 20),
            color: SaraColors.secondary,
            onPressed: () => Navigator.push(
              context, MaterialPageRoute(builder: (_) => const MemoryScreen()),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.trending_up, size: 20),
            color: SaraColors.secondary,
            tooltip: 'SABE',
            onPressed: () => Navigator.push(
              context, MaterialPageRoute(builder: (_) => const BettingScreen()),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.shield_outlined, size: 20),
            color: SaraColors.dim,
            tooltip: 'Control parental',
            onPressed: () => Navigator.push(
              context, MaterialPageRoute(builder: (_) => const MonitoringSetupScreen()),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.logout, size: 20),
            color: SaraColors.dim,
            tooltip: 'Cerrar sesión',
            onPressed: () async {
              await AuthService().signOut();
              if (!mounted) return;
              Navigator.of(context).pushAndRemoveUntil(
                MaterialPageRoute(builder: (_) => LoginScreen(
                  onSignedIn: () => Navigator.of(context).pushAndRemoveUntil(
                    MaterialPageRoute(builder: (_) => const ChatScreen()),
                    (_) => false,
                  ),
                )),
                (_) => false,
              );
            },
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
                // Botón micrófono
                if (_sttAvailable)
                  GestureDetector(
                    onTap: _toggleListen,
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 150),
                      width: 46, height: 46,
                      decoration: BoxDecoration(
                        color: _isListening
                            ? const Color(0xFFBF360C)
                            : SaraColors.surface,
                        borderRadius: BorderRadius.circular(13),
                        border: Border.all(color: const Color(0x0FFFFFFF)),
                        boxShadow: _isListening ? [
                          BoxShadow(
                            color: const Color(0xFFBF360C).withOpacity(0.4),
                            blurRadius: 8,
                          ),
                        ] : null,
                      ),
                      child: Icon(
                        _isListening ? Icons.mic_rounded : Icons.mic_none_rounded,
                        size: 20,
                        color: _isListening ? Colors.white : SaraColors.dim,
                      ),
                    ),
                  ),
                const SizedBox(width: 6),
                // Botón enviar
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
