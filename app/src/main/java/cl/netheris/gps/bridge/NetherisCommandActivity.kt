package cl.netheris.gps.bridge

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import androidx.core.content.ContextCompat
import cl.netheris.gps.nav.NavigationForegroundService

/**
 * Lightweight command entry point for Netheris integrations.
 *
 * Supported URIs:
 *   netheris://navigate?lat=-33.45&lon=-70.66&label=Casa
 *   netheris://stop
 *   netheris://bridge-test
 *
 * Bridge URL/token configuration is intentionally NOT accepted through a URI
 * because secrets in deep links may be exposed in logs/history. Configure it
 * locally through NetherisBridge.configure(...) or a future settings screen.
 */
class NetherisCommandActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handle(intent)
        finish()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handle(intent)
        finish()
    }

    private fun handle(intent: Intent?) {
        val uri = intent?.data ?: return
        if (uri.scheme != "netheris") return
        when (uri.host) {
            "navigate" -> {
                val lat = uri.getQueryParameter("lat")?.toDoubleOrNull() ?: return
                val lon = uri.getQueryParameter("lon")?.toDoubleOrNull() ?: return
                val label = uri.getQueryParameter("label")?.takeIf { it.isNotBlank() } ?: "Destino Netheris"
                val service = Intent(this, NavigationForegroundService::class.java)
                    .setAction(NavigationForegroundService.ACTION_START)
                    .putExtra(NavigationForegroundService.EXTRA_LABEL, label)
                    .putExtra(NavigationForegroundService.EXTRA_LAT, lat)
                    .putExtra(NavigationForegroundService.EXTRA_LON, lon)
                ContextCompat.startForegroundService(this, service)
            }
            "stop" -> {
                startService(Intent(this, NavigationForegroundService::class.java).setAction(NavigationForegroundService.ACTION_STOP))
            }
            "bridge-test" -> NetherisBridge.test(this)
        }
    }
}
