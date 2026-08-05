import 'package:firebase_analytics/firebase_analytics.dart';

class AnalyticsService {
  static final FirebaseAnalytics analytics = FirebaseAnalytics.instance;

  static Future<void> logAppOpen() async {
    await analytics.logAppOpen();
  }

  static Future<void> logLogin() async {
    await analytics.logLogin(loginMethod: "JWT");
  }

  static Future<void> logWorkoutStarted(String workoutName) async {
    await analytics.logEvent(
      name: "workout_started",
      parameters: {
        "workout_name": workoutName,
      },
    );
  }

  static Future<void> logWorkoutCompleted(String workoutName) async {
    await analytics.logEvent(
      name: "workout_completed",
      parameters: {
        "workout_name": workoutName,
      },
    );
  }
}