import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'api.dart';
import 'theme.dart';
import 'screens/chat_screen.dart';
import 'services/sync_service.dart';
import 'monitoring/monitoring_channel.dart';

// Canal de notificaciones para Android
const _channel = AndroidNotificationChannel(
  'sara_reminders',
  'Recordatorios SARA',
  description: 'Notificaciones de recordatorios de SARA',
  importance: Importance.max,
  sound: RawResourceAndroidNotificationSound('notification'),
  playSound: true,
);

final FlutterLocalNotificationsPlugin _localNotif =
    FlutterLocalNotificationsPlugin();

// Handler para mensajes en background (debe ser top-level)
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  // FCM ya muestra la notificación automáticamente en background
}

Future<void> _initNotifications() async {
  await Firebase.initializeApp();

  // Configurar canal Android
  await _localNotif
      .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>()
      ?.createNotificationChannel(_channel);

  // Inicializar local notifications para foreground
  const initSettings = InitializationSettings(
    android: AndroidInitializationSettings('@mipmap/ic_launcher'),
  );
  await _localNotif.initialize(initSettings);

  // Pedir permisos
  await FirebaseMessaging.instance.requestPermission(
    alert: true,
    badge: true,
    sound: true,
  );

  // Handler background
  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

  // Handler foreground — mostrar notificación local
  FirebaseMessaging.onMessage.listen((RemoteMessage message) {
    final notification = message.notification;
    if (notification == null) return;

    _localNotif.show(
      notification.hashCode,
      notification.title,
      notification.body,
      NotificationDetails(
        android: AndroidNotificationDetails(
          _channel.id,
          _channel.name,
          channelDescription: _channel.description,
          importance: Importance.max,
          priority: Priority.high,
          icon: '@mipmap/ic_launcher',
        ),
      ),
    );
  });

  // Obtener y registrar el FCM token
  final token = await FirebaseMessaging.instance.getToken();
  if (token != null) {
    await registerFcmToken(token);
  }

  // Renovar token automáticamente si cambia
  FirebaseMessaging.instance.onTokenRefresh.listen(registerFcmToken);
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: Color(0xFF1A1C1E),
    systemNavigationBarIconBrightness: Brightness.light,
  ));

  await _initNotifications();
  await SyncService().init();
  // Auto-registrar dispositivo y sincronizar estado de monitoreo con el padre
  MonitoringChannel.registerAndSync();

  runApp(const SaraApp());
}

class SaraApp extends StatelessWidget {
  const SaraApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SARA',
      debugShowCheckedModeBanner: false,
      theme: saraTheme(),
      home: const ChatScreen(),
    );
  }
}
