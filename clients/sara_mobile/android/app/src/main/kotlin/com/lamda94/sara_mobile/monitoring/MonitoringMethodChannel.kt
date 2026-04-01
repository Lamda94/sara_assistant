package com.lamda94.sara_mobile.monitoring

import android.app.AppOpsManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.provider.Settings
import android.text.TextUtils
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugin.common.MethodCall

class MonitoringMethodChannel(private val context: Context) {

    companion object {
        const val CHANNEL = "com.lamda94.sara_mobile/monitoring"
    }

    fun handle(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "startMonitoring" -> {
                val childSessionId = call.argument<String>("childSessionId") ?: ""
                MonitoringRepository.setChildSessionId(context, childSessionId)
                MonitoringRepository.setMonitoringEnabled(context, true)
                val svc = Intent(context, MonitoringForegroundService::class.java)
                context.startForegroundService(svc)
                MonitoringSyncWorker.schedulePeriodic(context)
                result.success(true)
            }
            "stopMonitoring" -> {
                MonitoringRepository.setMonitoringEnabled(context, false)
                context.stopService(Intent(context, MonitoringForegroundService::class.java))
                result.success(true)
            }
            "checkPermissions" -> {
                result.success(mapOf(
                    "usageStats" to hasUsageStatsPermission(),
                    "notificationListener" to hasNotificationListenerPermission(),
                    "accessibility" to hasAccessibilityPermission(),
                ))
            }
            "openUsageAccessSettings" -> {
                context.startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                result.success(null)
            }
            "openNotificationAccessSettings" -> {
                context.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                result.success(null)
            }
            "openAccessibilitySettings" -> {
                context.startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                result.success(null)
            }
            "openBatteryOptimizationSettings" -> {
                context.startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                result.success(null)
            }
            else -> result.notImplemented()
        }
    }

    private fun hasUsageStatsPermission(): Boolean {
        val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
        val mode = appOps.unsafeCheckOpNoThrow(
            AppOpsManager.OPSTR_GET_USAGE_STATS,
            android.os.Process.myUid(),
            context.packageName
        )
        return mode == AppOpsManager.MODE_ALLOWED
    }

    private fun hasNotificationListenerPermission(): Boolean {
        val enabled = Settings.Secure.getString(
            context.contentResolver,
            "enabled_notification_listeners"
        ) ?: return false
        val componentName = ComponentName(context, SaraNotificationListener::class.java)
        return enabled.contains(componentName.flattenToString())
    }

    private fun hasAccessibilityPermission(): Boolean {
        val enabled = Settings.Secure.getString(
            context.contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ) ?: return false
        val componentName = ComponentName(context, SaraAccessibilityService::class.java)
        return enabled.contains(componentName.flattenToString())
    }
}
