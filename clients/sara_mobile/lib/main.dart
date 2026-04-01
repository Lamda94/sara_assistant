import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'api.dart';
import 'theme.dart';
import 'screens/chat_screen.dart';
import 'screens/login_screen.dart';
import 'services/auth_service.dart';
import 'services/sync_service.dart';
import 'monitoring/monitoring_channel.dart';

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

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
}

Future<void> _initNotifications() async {
  await Firebase.initializeApp();

  await _localNotif
      .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>()
      ?.createNotificationChannel(_channel);

  const initSettings = InitializationSettings(
    android: AndroidInitializationSettings('@mipmap/ic_launcher'),
  );
  await _localNotif.initialize(initSettings);

  await FirebaseMessaging.instance.requestPermission(
    alert: true, badge: true, sound: true,
  );

  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

  FirebaseMessaging.onMessage.listen((RemoteMessage message) {
    final notification = message.notification;
    if (notification == null) return;
    _localNotif.show(
      notification.hashCode,
      notification.title,
      notification.body,
      NotificationDetails(
        android: AndroidNotificationDetails(
          _channel.id, _channel.name,
          channelDescription: _channel.description,
          importance: Importance.max,
          priority: Priority.high,
          icon: '@mipmap/ic_launcher',
        ),
      ),
    );
  });

  final token = await FirebaseMessaging.instance.getToken();
  if (token != null) await registerFcmToken(token);
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
  MonitoringChannel.registerAndSync();

  // Intentar login silencioso
  await AuthService().tryAutoSignIn();

  runApp(const SaraApp());
}

class SaraApp extends StatefulWidget {
  const SaraApp({super.key});

  @override
  State<SaraApp> createState() => _SaraAppState();
}

class _SaraAppState extends State<SaraApp> {
  bool _signedIn = AuthService().isSignedIn;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SARA',
      debugShowCheckedModeBanner: false,
      theme: saraTheme(),
      home: _signedIn
          ? const ChatScreen()
          : LoginScreen(onSignedIn: () => setState(() => _signedIn = true)),
    );
  }
}
