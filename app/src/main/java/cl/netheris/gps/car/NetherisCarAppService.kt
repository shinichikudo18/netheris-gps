package cl.netheris.gps.car

import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import androidx.car.app.CarAppService
import androidx.car.app.CarContext
import androidx.car.app.Screen
import androidx.car.app.Session
import androidx.car.app.SessionInfo
import androidx.car.app.model.Action
import androidx.car.app.model.Pane
import androidx.car.app.model.PaneTemplate
import androidx.car.app.model.Row
import androidx.car.app.model.Template
import androidx.car.app.validation.HostValidator
import androidx.core.content.ContextCompat
import cl.netheris.gps.core.NavStateStore
import cl.netheris.gps.nav.NavigationForegroundService
import org.json.JSONArray

private const val PREFS_NAME = "netheris_gps"
private const val HOME_LAT = "home_lat"
private const val HOME_LON = "home_lon"
private const val FAVORITE_LAT = "favorite_lat"
private const val FAVORITE_LON = "favorite_lon"
private const val FAVORITE_LABEL = "favorite_label"
private const val RECENTS_JSON = "recents_json"

class NetherisCarAppService : CarAppService() {
    override fun createHostValidator(): HostValidator {
        return if ((applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0) {
            HostValidator.ALLOW_ALL_HOSTS_VALIDATOR
        } else {
            HostValidator.Builder(this)
                .addAllowedHosts(androidx.car.app.R.array.hosts_allowlist_sample)
                .build()
        }
    }

    override fun onCreateSession(sessionInfo: SessionInfo): Session = NetherisCarSession()
}

private class NetherisCarSession : Session() {
    override fun onCreateScreen(intent: Intent): Screen = NetherisHomeScreen(carContext)
}

private class NetherisHomeScreen(carContext: CarContext) : Screen(carContext) {

    private fun startNavigation(label: String, lat: Double, lon: Double) {
        val intent = Intent(carContext, NavigationForegroundService::class.java)
            .setAction(NavigationForegroundService.ACTION_START)
            .putExtra(NavigationForegroundService.EXTRA_LABEL, label)
            .putExtra(NavigationForegroundService.EXTRA_LAT, lat)
            .putExtra(NavigationForegroundService.EXTRA_LON, lon)
        ContextCompat.startForegroundService(carContext, intent)
        invalidate()
    }

    private fun stopNavigation() {
        carContext.startService(
            Intent(carContext, NavigationForegroundService::class.java)
                .setAction(NavigationForegroundService.ACTION_STOP)
        )
        invalidate()
    }

    override fun onGetTemplate(): Template {
        val prefs = carContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val nav = NavStateStore.snapshot(carContext)
        val pane = Pane.Builder()

        if (nav.active || nav.destination.isNotBlank()) {
            pane.addRow(
                Row.Builder()
                    .setTitle(if (nav.active) "Navegando · ${nav.destination.ifBlank { "Destino" }}" else "Último destino · ${nav.destination}")
                    .addText(nav.instruction.ifBlank { "Esperando posición GPS…" })
                    .addText(listOf(nav.nextDistance, nav.remaining, nav.eta, nav.speed).filter { it.isNotBlank() }.joinToString(" · "))
                    .build()
            )
            if (nav.active) {
                pane.addAction(
                    Action.Builder()
                        .setTitle("Detener")
                        .setOnClickListener { stopNavigation() }
                        .build()
                )
            }
        } else {
            pane.addRow(
                Row.Builder()
                    .setTitle("Netheris GPS v2.5")
                    .addText("Selecciona un destino para iniciar navegación")
                    .build()
            )
        }

        if (prefs.contains(HOME_LAT) && prefs.contains(HOME_LON)) {
            val lat = prefs.getLong(HOME_LAT, 0L).let(Double::fromBits)
            val lon = prefs.getLong(HOME_LON, 0L).let(Double::fromBits)
            pane.addRow(
                Row.Builder()
                    .setTitle("Casa · Netheris")
                    .addText("Iniciar ruta a Casa")
                    .setOnClickListener { startNavigation("Casa · Netheris", lat, lon) }
                    .build()
            )
        }

        if (prefs.contains(FAVORITE_LAT) && prefs.contains(FAVORITE_LON)) {
            val lat = prefs.getLong(FAVORITE_LAT, 0L).let(Double::fromBits)
            val lon = prefs.getLong(FAVORITE_LON, 0L).let(Double::fromBits)
            val label = prefs.getString(FAVORITE_LABEL, "Favorito") ?: "Favorito"
            pane.addRow(
                Row.Builder()
                    .setTitle("Favorito · $label")
                    .addText("Iniciar ruta")
                    .setOnClickListener { startNavigation(label, lat, lon) }
                    .build()
            )
        }

        val recents = runCatching { JSONArray(prefs.getString(RECENTS_JSON, "[]") ?: "[]") }.getOrDefault(JSONArray())
        val count = minOf(recents.length(), 2)
        for (i in 0 until count) {
            val item = recents.optJSONObject(i) ?: continue
            val label = item.optString("label", "Destino reciente")
            val lat = item.optDouble("lat", Double.NaN)
            val lon = item.optDouble("lon", Double.NaN)
            if (!lat.isNaN() && !lon.isNaN()) {
                pane.addRow(
                    Row.Builder()
                        .setTitle("Reciente · ${label.substringBefore(",").take(35)}")
                        .addText("Iniciar ruta")
                        .setOnClickListener { startNavigation(label, lat, lon) }
                        .build()
                )
            }
        }

        pane.addAction(
            Action.Builder()
                .setTitle("Actualizar")
                .setOnClickListener { invalidate() }
                .build()
        )

        return PaneTemplate.Builder(pane.build())
            .setTitle("Netheris GPS")
            .setHeaderAction(Action.APP_ICON)
            .build()
    }
}
