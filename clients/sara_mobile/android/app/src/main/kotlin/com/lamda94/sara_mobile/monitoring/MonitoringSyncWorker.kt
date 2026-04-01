package com.lamda94.sara_mobile.monitoring

import android.content.Context
import androidx.work.*
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit

class MonitoringSyncWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {

    companion object {
        private const val WORK_NAME_PERIODIC = "sara_monitoring_periodic"
        private const val WORK_NAME_IMMEDIATE = "sara_monitoring_immediate"

        fun schedulePeriodic(ctx: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            val request = PeriodicWorkRequestBuilder<MonitoringSyncWorker>(15, TimeUnit.MINUTES)
                .setConstraints(constraints)
                .build()
            WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
                WORK_NAME_PERIODIC,
                ExistingPeriodicWorkPolicy.KEEP,
                request,
            )
        }

        fun triggerImmediateSync(ctx: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            val request = OneTimeWorkRequestBuilder<MonitoringSyncWorker>()
                .setConstraints(constraints)
                .build()
            WorkManager.getInstance(ctx).enqueueUniqueWork(
                WORK_NAME_IMMEDIATE,
                ExistingWorkPolicy.REPLACE,
                request,
            )
        }
    }

    override fun doWork(): Result {
        val payload = MonitoringRepository.drainAll(applicationContext)
        val childId = payload.optString("child_session_id")
        if (childId.isEmpty()) return Result.success()

        val hasData = listOf("app_usage", "notifications", "browser", "packages")
            .any { payload.optJSONArray(it)?.length() ?: 0 > 0 }
        if (!hasData) return Result.success()

        return try {
            val baseUrl = getBaseUrl()
            post("$baseUrl/monitoring/batch", payload.toString())

            // Si hay notificaciones sospechosas, alertar también por endpoint dedicado
            val notifs = payload.optJSONArray("notifications") ?: return Result.success()
            for (i in 0 until notifs.length()) {
                val n = notifs.getJSONObject(i)
                if (n.optBoolean("is_suspicious")) {
                    val alert = org.json.JSONObject().apply {
                        put("child_session_id", childId)
                        put("package_name", n.optString("package_name"))
                        put("title", n.optString("title"))
                        put("body", n.optString("body"))
                        put("posted_at", n.optLong("posted_at"))
                    }
                    post("$baseUrl/monitoring/suspicious", alert.toString())
                }
            }
            Result.success()
        } catch (e: Exception) {
            // Restaurar los datos si falla para no perderlos
            e.printStackTrace()
            Result.retry()
        }
    }

    private fun post(urlStr: String, body: String) {
        val conn = URL(urlStr).openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.setRequestProperty("Content-Type", "application/json")
        conn.doOutput = true
        conn.connectTimeout = 10_000
        conn.readTimeout = 10_000
        conn.outputStream.use { it.write(body.toByteArray()) }
        conn.responseCode  // trigger request
        conn.disconnect()
    }

    private fun getBaseUrl(): String {
        val prefs = applicationContext.getSharedPreferences("FlutterSharedPreferences", Context.MODE_PRIVATE)
        return prefs.getString("flutter.base_url", "https://api.luismendezdev.online") ?: "https://api.luismendezdev.online"
    }
}
