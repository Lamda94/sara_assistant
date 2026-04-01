package com.lamda94.sara_mobile.monitoring

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject

/**
 * Buffer local de eventos de monitoreo.
 * Los eventos se guardan en SharedPreferences como JSON hasta que
 * el WorkManager los sincroniza con el backend cada 15 minutos.
 */
object MonitoringRepository {

    private const val PREFS_NAME = "sara_monitoring"
    private const val KEY_APP_USAGE = "pending_app_usage"
    private const val KEY_NOTIFICATIONS = "pending_notifications"
    private const val KEY_BROWSER = "pending_browser"
    private const val KEY_PACKAGES = "pending_packages"
    private const val KEY_ENABLED = "monitoring_enabled"
    private const val KEY_CHILD_SESSION = "child_session_id"

    private fun prefs(ctx: Context): SharedPreferences =
        ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun isMonitoringEnabled(ctx: Context) = prefs(ctx).getBoolean(KEY_ENABLED, false)

    fun setMonitoringEnabled(ctx: Context, enabled: Boolean) {
        prefs(ctx).edit().putBoolean(KEY_ENABLED, enabled).apply()
    }

    fun getChildSessionId(ctx: Context): String =
        prefs(ctx).getString(KEY_CHILD_SESSION, "") ?: ""

    fun setChildSessionId(ctx: Context, sessionId: String) {
        prefs(ctx).edit().putString(KEY_CHILD_SESSION, sessionId).apply()
    }

    fun enqueueAppUsage(ctx: Context, items: JSONArray) = appendToList(ctx, KEY_APP_USAGE, items)

    fun enqueueNotification(ctx: Context, event: JSONObject, isSuspicious: Boolean) {
        appendToList(ctx, KEY_NOTIFICATIONS, JSONArray().put(event))
        if (isSuspicious) {
            // Envío inmediato en segundo plano
            MonitoringSyncWorker.triggerImmediateSync(ctx)
        }
    }

    fun enqueueBrowserEvent(ctx: Context, event: JSONObject) =
        appendToList(ctx, KEY_BROWSER, JSONArray().put(event))

    fun enqueuePackageEvent(ctx: Context, event: JSONObject) =
        appendToList(ctx, KEY_PACKAGES, JSONArray().put(event))

    fun drainAll(ctx: Context): JSONObject {
        val p = prefs(ctx)
        val result = JSONObject().apply {
            put("child_session_id", getChildSessionId(ctx))
            put("app_usage", drain(p, KEY_APP_USAGE))
            put("notifications", drain(p, KEY_NOTIFICATIONS))
            put("browser", drain(p, KEY_BROWSER))
            put("packages", drain(p, KEY_PACKAGES))
        }
        return result
    }

    private fun drain(prefs: SharedPreferences, key: String): JSONArray {
        val raw = prefs.getString(key, "[]") ?: "[]"
        prefs.edit().remove(key).apply()
        return try { JSONArray(raw) } catch (_: Exception) { JSONArray() }
    }

    private fun appendToList(ctx: Context, key: String, items: JSONArray) {
        val p = prefs(ctx)
        val existing = try { JSONArray(p.getString(key, "[]")) } catch (_: Exception) { JSONArray() }
        for (i in 0 until items.length()) existing.put(items.get(i))
        p.edit().putString(key, existing.toString()).apply()
    }
}
