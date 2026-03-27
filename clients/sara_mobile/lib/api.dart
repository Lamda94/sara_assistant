import 'dart:convert';
import 'package:http/http.dart' as http;

const String kBaseUrl = 'https://api.luismendezdev.online';
const String kSessionId = 'lamda94-mobile';
const String kDevice = 'mobile';

class ChatMessage {
  final String id;
  final String role;
  final String content;
  final String device;
  final DateTime time;
  final bool isTyping;
  // true = enviado sin conexión, esperando sync
  final bool pending;

  ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.device,
    required this.time,
    this.isTyping = false,
    this.pending = false,
  });

  ChatMessage copyWith({String? content, bool? isTyping, String? device, bool? pending}) {
    return ChatMessage(
      id: id,
      role: role,
      content: content ?? this.content,
      device: device ?? this.device,
      time: time,
      isTyping: isTyping ?? this.isTyping,
      pending: pending ?? this.pending,
    );
  }
}

class Memory {
  final String id;
  final String content;

  Memory({required this.id, required this.content});

  factory Memory.fromJson(Map<String, dynamic> j) => Memory(
    id: j['id'] ?? '',
    content: j['memory'] ?? j['content'] ?? '',
  );
}

Future<String> sendChat(String message) async {
  final res = await http.post(
    Uri.parse('$kBaseUrl/chat'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'message': message,
      'session_id': kSessionId,
      'device': kDevice,
    }),
  ).timeout(const Duration(seconds: 30));

  if (res.statusCode == 200) {
    return jsonDecode(res.body)['response'] as String;
  }
  throw Exception('Error ${res.statusCode}');
}

Future<List<Memory>> getMemories() async {
  final res = await http.get(Uri.parse('$kBaseUrl/memory/$kSessionId'))
      .timeout(const Duration(seconds: 15));
  if (res.statusCode == 200) {
    final data = jsonDecode(res.body);
    return (data['facts'] as List).map((m) => Memory.fromJson(m)).toList();
  }
  throw Exception('Error obteniendo memoria');
}

Future<void> registerFcmToken(String token) async {
  try {
    await http.post(
      Uri.parse('$kBaseUrl/notifications/register-token'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'session_id': kSessionId, 'token': token}),
    ).timeout(const Duration(seconds: 10));
  } catch (_) {
    // No crítico si falla
  }
}
