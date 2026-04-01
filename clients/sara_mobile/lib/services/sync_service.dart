import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../api.dart';
import 'local_db.dart';

/// Callback que se dispara cuando un mensaje offline recibe su respuesta.
typedef SyncCallback = void Function(String localId, String response);

/// Servicio singleton que gestiona conectividad y cola de mensajes offline.
class SyncService {
  static final SyncService _instance = SyncService._internal();
  factory SyncService() => _instance;
  SyncService._internal();

  final _connectivity = Connectivity();
  bool _isOnline = true;
  bool _syncing = false;

  /// Notifica cambios de conectividad a los listeners (ej. ChatScreen).
  final _statusController = StreamController<bool>.broadcast();
  Stream<bool> get onlineStream => _statusController.stream;
  bool get isOnline => _isOnline;

  /// La UI registra este callback para actualizar mensajes al sincronizar.
  SyncCallback? onMessageSynced;

  Future<void> init() async {
    final result = await _connectivity.checkConnectivity();
    _isOnline = _connected(result);

    _connectivity.onConnectivityChanged.listen((result) {
      final wasOnline = _isOnline;
      _isOnline = _connected(result);
      _statusController.add(_isOnline);
      // Volvió la conexión → procesar cola pendiente
      if (!wasOnline && _isOnline) {
        _processQueue();
      }
    });
  }

  bool _connected(List<ConnectivityResult> result) =>
      result.any((r) => r != ConnectivityResult.none);

  /// Envía el mensaje si hay conexión; si no, lo guarda en SQLite.
  /// Devuelve la respuesta del asistente o null si quedó en cola.
  Future<String?> sendOrQueue(String localId, String content,
      {String? googleAccessToken}) async {
    if (_isOnline) {
      try {
        return await sendChat(content, googleAccessToken: googleAccessToken);
      } catch (_) {
        await _enqueue(localId, content);
        return null;
      }
    } else {
      await _enqueue(localId, content);
      return null;
    }
  }

  Future<void> _enqueue(String localId, String content) async {
    await LocalDb.insertPending(PendingMessage(
      localId: localId,
      content: content,
      createdAt: DateTime.now(),
    ));
  }

  /// Procesa la cola en orden, enviando cada mensaje pendiente.
  Future<void> _processQueue() async {
    if (_syncing) return;
    _syncing = true;
    try {
      final pending = await LocalDb.getPending();
      for (final msg in pending) {
        try {
          final response = await sendChat(msg.content);
          await LocalDb.markSynced(msg.localId, response);
          onMessageSynced?.call(msg.localId, response);
        } catch (_) {
          break; // Si falla un mensaje, parar y reintentar en la próxima reconexión
        }
      }
      await LocalDb.deleteSynced();
    } finally {
      _syncing = false;
    }
  }

  void dispose() {
    _statusController.close();
  }
}
