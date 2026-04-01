package com.lamda94.sara_mobile.monitoring

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import org.json.JSONObject

class PackageChangeReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val pkg = intent.data?.schemeSpecificPart ?: return
        val eventType = when (intent.action) {
            Intent.ACTION_PACKAGE_ADDED -> "install"
            Intent.ACTION_PACKAGE_REMOVED -> "uninstall"
            else -> return
        }
        val label = try {
            context.packageManager
                .getApplicationLabel(context.packageManager.getApplicationInfo(pkg, 0))
                .toString()
        } catch (_: PackageManager.NameNotFoundException) { pkg }

        val ev = JSONObject().apply {
            put("package_name", pkg)
            put("app_label", label)
            put("event_type", eventType)
            put("occurred_at", System.currentTimeMillis())
        }
        MonitoringRepository.enqueuePackageEvent(context, ev)
    }
}
