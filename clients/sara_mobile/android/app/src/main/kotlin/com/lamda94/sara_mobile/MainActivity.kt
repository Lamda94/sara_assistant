package com.lamda94.sara_mobile

import com.lamda94.sara_mobile.monitoring.MonitoringMethodChannel
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        val monitoringChannel = MonitoringMethodChannel(applicationContext)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, MonitoringMethodChannel.CHANNEL)
            .setMethodCallHandler { call, result -> monitoringChannel.handle(call, result) }
    }
}
