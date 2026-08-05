import 'package:firebase_messaging/firebase_messaging.dart';
import '../api_service.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NotificationService {
  static final FirebaseMessaging _messaging = FirebaseMessaging.instance;
  static final FlutterLocalNotificationsPlugin _localNotifications = FlutterLocalNotificationsPlugin();

  /// Initialize Firebase Cloud Messaging
  static Future<void> initialize() async {
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const initSettings = InitializationSettings(android: androidSettings);
    await _localNotifications.initialize(initSettings);

    const channel = AndroidNotificationChannel(
      'rise_back_channel',
      'Rise Back Notifications',
      description: 'Notifications from your Rise Back mentor and progress alerts',
      importance: Importance.high,
    );

    await _localNotifications
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channel);
    // Request notification permission
    NotificationSettings settings = await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );

    print("Notification Permission: ${settings.authorizationStatus}");

    // Get FCM Token
    String? token = await _messaging.getToken();

    print("=========================================");
    print("FCM TOKEN:");
    print(token);
    print("=========================================");

    if (token != null) {
      final registered = await ApiService.registerDevice(token);
      print("Device registered with backend: $registered");
    }

    // Refresh token listener
    FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
      print("New FCM Token:");
      print(newToken);
    });

    // Foreground notification listener
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      print("Foreground Notification Received!");

      if (message.notification != null) {
        print("Title: ${message.notification!.title}");
        print("Body : ${message.notification!.body}");

        _localNotifications.show(
          message.hashCode,
          message.notification!.title,
          message.notification!.body,
          const NotificationDetails(
            android: AndroidNotificationDetails(
              'rise_back_channel',
              'Rise Back Notifications',
              channelDescription: 'Notifications from your Rise Back mentor and progress alerts',
              importance: Importance.high,
              priority: Priority.high,
            ),
          ),
        );
      }

      if (message.data.isNotEmpty) {
        print("Data: ${message.data}");
      }
    });

    // Notification tapped while app in background
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      print("Notification clicked!");
      print(message.data);
    });
  }
}