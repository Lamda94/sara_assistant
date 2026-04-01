package com.lamda94.sara_mobile.monitoring

import android.app.*
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import androidx.core.app.NotificationCompat
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.*

class MonitoringForegroundService : Service() {

    private val handler = Handler(Looper.getMainLooper())
    private val POLL_INTERVAL_MS = 15 * 60 * 1000L  // 15 minutos
    private val CHANNEL_ID = "sara_monitoring"
    private val NOTIF_ID = 9001
    private var lastPollTime = 0L

    private val pollRunnable = object : Runnable {
        override fun run() {
            collectAndSync()
            handler.postDelayed(this, POLL_INTERVAL_MS)
        }
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIF_ID, buildNotification())
        lastPollTime = System.currentTimeMillis() - POLL_INTERVAL_MS
        handler.postDelayed(pollRunnable, POLL_INTERVAL_MS)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        handler.removeCallbacks(pollRunnable)
        super.onDestroy()
    }

    private fun collectAndSync() {
        try {
            val usm = getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
            val now = System.currentTimeMillis()
            val stats = usm.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, lastPollTime, now)

            val appUsageList = JSONArray()
            val sdf = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
            val today = sdf.format(Date())
            val pm = packageManager

            stats?.filter { it.totalTimeInForeground > 0 }?.forEach { stat ->
                val appLabel = try {
                    pm.getApplicationLabel(pm.getApplicationInfo(stat.packageName, 0)).toString()
                } catch (_: PackageManager.NameNotFoundException) {
                    stat.packageName
                }
                val item = JSONObject().apply {
                    put("package_name", stat.packageName)
                    put("app_label", appLabel)
                    put("foreground_ms", stat.totalTimeInForeground)
                    put("launches", if (android.os.Build.VERSION.SDK_INT >= 29) stat.appLaunchCount else 0)
                    put("event_date", today)
                }
                appUsageList.put(item)
            }

            lastPollTime = now

            // Enviar al repositorio local para que el WorkManager lo sincronice
            MonitoringRepository.enqueueAppUsage(applicationContext, appUsageList)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun buildNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("SARA")
            .setContentText("Protección activa")
            .setSmallIcon(android.R.drawable.ic_lock_silent_mode_off)
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .setSilent(true)
            .build()
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "SARA Control Parental",
            NotificationManager.IMPORTANCE_MIN
        ).apply { description = "Servicio de monitoreo activo" }
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(channel)
    }
}
