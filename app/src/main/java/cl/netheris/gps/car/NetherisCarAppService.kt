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
import org.json.JSONArray

private const val PREFS_NAME = "netheris_gps"
private const val HOME_LAT = "home_lat"
private const val HOME_LON = "home_lon"
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

    override fun onGetTemplate(): Template {
        val prefs = carContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val hasHome = prefs.contains(HOME_LAT) && prefs.contains(HOME_LON)
        val favorite = prefs.getString(FAVORITE_LABEL, null)?.takeIf { it.isNotBlank() }
        val recentsCount = runCatching {
            JSONArray(prefs.getString(RECENTS_JSON, "[]") ?: "[]").length()
        }.getOrDefault(0)

        val paneBuilder = Pane.Builder()
            .addRow(
                Row.Builder()
                    .setTitle("Android Auto conectado")
                    .addText("Netheris GPS v2.0 listo en el vehículo")
                    .build()
            )
            .addRow(
                Row.Builder()
                    .setTitle(if (hasHome) "Casa configurada" else "Casa sin configurar")
                    .addText(if (hasHome) "Disponible desde la app del teléfono" else "Guárdala primero en el teléfono")
                    .build()
            )

        if (favorite != null) {
            paneBuilder.addRow(
                Row.Builder()
                    .setTitle("Favorito")
                    .addText(favorite.take(80))
                    .build()
            )
        }

        paneBuilder.addRow(
            Row.Builder()
                .setTitle("Destinos recientes")
                .addText("$recentsCount guardados")
                .build()
        )

        return PaneTemplate.Builder(paneBuilder.build())
            .setTitle("Netheris GPS")
            .setHeaderAction(Action.APP_ICON)
            .build()
    }
}
