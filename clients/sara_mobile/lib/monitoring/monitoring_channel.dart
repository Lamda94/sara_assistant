import 'package:flutter/services.dart';

class MonitoringChannel {
  static const _channel = MethodChannel('com.lamda94.sara_mobile/monitoring');

  /// Auto-registro al iniciar la app. El padre controla la activación remotamente.
  static Future<void> registerAndSync() async {
    try {
      await _channel.invokeMethod('registerAndSync');
    } catch (_) {}
  }

  static Future<Map<String, bool>> checkPermissions() async {
    final result = await _channel.invokeMapMethod<String, bool>('checkPermissions');
    return result ?? {};
  }

  static Future<void> startMonitoring(String childSessionId) async {
    await _channel.invokeMethod('startMonitoring', {'childSessionId': childSessionId});
  }

  static Future<void> stopMonitoring() async {
    await _channel.invokeMethod('stopMonitoring');
  }

  static Future<void> openUsageAccessSettings() async {
    await _channel.invokeMethod('openUsageAccessSettings');
  }

  static Future<void> openNotificationAccessSettings() async {
    await _channel.invokeMethod('openNotificationAccessSettings');
  }

  static Future<void> openAccessibilitySettings() async {
    await _channel.invokeMethod('openAccessibilitySettings');
  }

  static Future<void> openBatterySettings() async {
    await _channel.invokeMethod('openBatteryOptimizationSettings');
  }
}
