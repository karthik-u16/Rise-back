import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'api_service.dart';
import 'services/notification_service.dart';
import 'services/analytics_service.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  await NotificationService.initialize();
  await AnalyticsService.logAppOpen();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: TestScreen(),
    );
  }
}

class TestScreen extends StatefulWidget {
  const TestScreen({super.key});

  @override
  State<TestScreen> createState() => _TestScreenState();
}

class _TestScreenState extends State<TestScreen> {
  String result = "Not tested yet";

  Future<void> testLogin() async {
    setState(() => result = "Loading...");
    final response = await ApiService.login("karthikeyan", "77");
    
    if (response["success"] == true) {
      final fcmToken = await FirebaseMessaging.instance.getToken();
      if (fcmToken != null) {
        final registered = await ApiService.registerDevice(fcmToken);
        print("Post-login device registration: $registered");
      }
    }

    setState(() => result = response.toString());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Rise Back - API Test")),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(result, textAlign: TextAlign.center),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: testLogin,
              child: const Text("Test Login"),
            ),
          ],
        ),
      ),
    );
  }
}