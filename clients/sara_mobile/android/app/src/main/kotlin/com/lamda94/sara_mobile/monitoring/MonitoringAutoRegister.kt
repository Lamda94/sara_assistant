package com.lamda94.sara_mobile.monitoring

import android.content.Context
import android.provider.Settings
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

object MonitoringAutoRegister {

    private const val PARENT_SESSION_ID = "lamda94"  // ID del padre (creador)
    private const val POLL_INTERVAL_MS = 5 * 60 * 1000L  // 5 minutos

    /** Registra este dispositivo y obtiene el estado de monitoreo del backend. */
    fun registerAndSync(ctx: Context) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val childId = getOrCreateChildSessionId(ctx)
                val androidId = Settings.Secure.getString(ctx.contentResolver, Settings.Secure.ANDROID_ID)
                val baseUrl = "https://api.luismendezdev.online"

                // Registrar dispositivo
                val regPayload = JSONObject().apply {
                    put("child_session_id", childId)
                    put("parent_session_id", PARENT_SESSION_ID)
                    put("device_label", android.os.Build.MODEL)
                    put("device_identifier", androidId)
                }
                post("$baseUrl/monitoring/register-child", regPayload.toString())

                // Consultar si el padre activó el monitoreo
                val statusJson = get("$baseUrl/monitoring/status/$childId")
                val enabled = JSONObject(statusJson).optBoolean("monitoring_enabled", false)

                val currentlyEnabled = MonitoringRepository.isMonitoringEnabled(ctx)
                if (enabled && !currentlyEnabled) {
                    MonitoringRepository.setMonitoringEnabled(ctx, true)
                    val svc = android.content.Intent(ctx, MonitoringForegroundService::class.java)
                    ctx.startForegroundService(svc)
                    MonitoringSyncWorker.schedulePeriodic(ctx)
                } else if (!enabled && currentlyEnabled) {
                    MonitoringRepository.setMonitoringEnabled(ctx, false)
                    ctx.stopService(android.content.Intent(ctx, MonitoringForegroundService::class.java))
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    fun getOrCreateChildSessionId(ctx: Context): String {
        val prefs = ctx.getSharedPreferences("sara_monitoring", Context.MODE_PRIVATE)
        var id = prefs.getString("child_session_id", null)
        if (id.isNullOrEmpty()) {
            val androidId = Settings.Secure.getString(ctx.contentResolver, Settings.Secure.ANDROID_ID)
            id = "child-$androidId"
            prefs.edit().putString("child_session_id", id).apply()
        }
        return id
    }

    private fun post(urlStr: String, body: String) {
        val conn = URL(urlStr).openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.setRequestProperty("Content-Type", "application/json")
        conn.doOutput = true
        conn.connectTimeout = 10_000
        conn.readTimeout = 10_000
        conn.outputStream.use { it.write(body.toByteArray()) }
        conn.responseCode
        conn.disconnect()
    }

    private fun get(urlStr: String): String {
        val conn = URL(urlStr).openConnection() as HttpURLConnection
        conn.requestMethod = "GET"
        conn.connectTimeout = 10_000
        conn.readTimeout = 10_000
        val response = conn.inputStream.bufferedReader().readText()
        conn.disconnect()
        return response
    }
}
