package com.lamda94.sara_mobile.monitoring

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import org.json.JSONObject

// Apps de mensajería y redes sociales monitorizadas
private val MONITORED_PACKAGES = setOf(
    "com.whatsapp",
    "com.whatsapp.w4b",
    "org.telegram.messenger",
    "com.instagram.android",
    "com.zhiliaoapp.musically",    // TikTok
    "com.snapchat.android",
    "com.facebook.orca",           // Messenger
    "com.facebook.katana",         // Facebook
    "com.twitter.android",
    "com.discord",
    "com.skype.raider",
    "com.google.android.apps.messaging",
    "com.samsung.android.messaging",
)

// Palabras clave sospechosas (configurable)
private val SUSPICIOUS_KEYWORDS = listOf(
    "secreto", "no le digas", "borrar", "delete", "escóndelo",
    "droga", "alcohol", "cerveza", "fiesta sin", "fugarnos",
    "novia secreta", "novio secreto", "te quiero esconder",
    "no le cuentes", "shhh", "entre nosotros",
)

class SaraNotificationListener : NotificationListenerService() {

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (sbn.packageName !in MONITORED_PACKAGES) return

        val extras = sbn.notification.extras ?: return
        val title = extras.getString(Notification.EXTRA_TITLE) ?: ""
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()
            ?: extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString()
            ?: ""

        val isSuspicious = SUSPICIOUS_KEYWORDS.any { kw ->
            text.lowercase().contains(kw) || title.lowercase().contains(kw)
        }

        val event = JSONObject().apply {
            put("package_name", sbn.packageName)
            put("title", title)
            put("body", text)
            put("is_suspicious", isSuspicious)
            put("posted_at", sbn.postTime)
        }

        MonitoringRepository.enqueueNotification(applicationContext, event, isSuspicious)
    }
}
