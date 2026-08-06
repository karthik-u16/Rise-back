import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiService {
  static const String baseUrl ="https://rise-back-rfuo.onrender.com";
  static const _storage = FlutterSecureStorage();

  static Future<Map<String, dynamic>> login(
    String username,
    String password,
  ) async {
    final response = await http.post(
      Uri.parse("$baseUrl/api/login"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({"username": username, "password": password}),
    );

    final data = jsonDecode(response.body);

    if (response.statusCode == 200) {
      await _storage.write(key: "jwt_token", value: data["token"]);
      return {"success": true, "data": data};
    } else {
      return {"success": false, "error": data["error"] ?? "Login failed"};
    }
  }

  static Future<Map<String, dynamic>?> getDashboard() async {
    final token = await _storage.read(key: "jwt_token");
    if (token == null) return null;

    final response = await http.get(
      Uri.parse("$baseUrl/api/dashboard"),
      headers: {"Authorization": "Bearer $token"},
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    return null;
  }

  static Future<void> logout() async {
    await _storage.delete(key: "jwt_token");
  }

  static Future<bool> registerDevice(String fcmToken) async {
    final token = await _storage.read(key: "jwt_token");
    if (token == null) return false;

    final response = await http.post(
      Uri.parse("$baseUrl/api/register-device"),
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer $token",
      },
      body: jsonEncode({"fcm_token": fcmToken}),
    );
    print("Register device status: ${response.statusCode}, body: ${response.body}");
    return response.statusCode == 200;
  }
}
