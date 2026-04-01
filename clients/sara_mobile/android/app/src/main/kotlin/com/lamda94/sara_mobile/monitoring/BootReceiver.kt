package com.lamda94.sara_mobile.monitoring

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED ||
            intent.action == Intent.ACTION_MY_PACKAGE_REPLACED
        ) {
            if (MonitoringRepository.isMonitoringEnabled(context)) {
                val svc = Intent(context, MonitoringForegroundService::class.java)
                context.startForegroundService(svc)
            }
        }
    }
}
