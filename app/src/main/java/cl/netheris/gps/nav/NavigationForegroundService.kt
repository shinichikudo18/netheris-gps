package cl.netheris.gps.nav

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.IBinder
import android.os.Looper
import android.os.SystemClock
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import cl.netheris.gps.MainActivity
import cl.netheris.gps.core.NavStateStore
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.max

class NavigationForegroundService : Service() {
    companion object {
        const val ACTION_START = "cl.netheris.gps.nav.START"
        const val ACTION_STOP = "cl.netheris.gps.nav.STOP"
        const val EXTRA_LAT = "lat"
        const val EXTRA_LON = "lon"
        const val EXTRA_LABEL = "label"
        private const val CHANNEL_ID = "netheris_navigation"
        private const val NOTIFICATION_ID = 2401
    }

    private data class P(val lat: Double, val lon: Double)
    private data class Step(val text: String, val point: P, val routeIndex: Int)
    private data class Route(val points: List<P>, val distance: Double, val duration: Double, val steps: List<Step>)

    private lateinit var locationManager: LocationManager
    private var listener: LocationListener? = null
    private var destination: P? = null
    private var destinationLabel: String = "Destino"
    private var route: Route? = null
    private var stepIndex = 0
    private var lastReroute = 0L

    override fun onCreate() {
        super.onCreate()
        locationManager = getSystemService(LOCATION_SERVICE) as LocationManager
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopNavigation()
                return START_NOT_STICKY
            }
            ACTION_START -> {
                val lat = intent.getDoubleExtra(EXTRA_LAT, Double.NaN)
                val lon = intent.getDoubleExtra(EXTRA_LON, Double.NaN)
                if (lat.isNaN() || lon.isNaN()) return START_NOT_STICKY
                destination = P(lat, lon)
                destinationLabel = intent.getStringExtra(EXTRA_LABEL)?.takeIf { it.isNotBlank() } ?: "Destino"
                NavStateStore.setDestination(this, destinationLabel, lat, lon)
                NavStateStore.setActive(this, true)
                startForeground(NOTIFICATION_ID, buildNotification("Preparando ruta…", destinationLabel))
                startLocationTracking()
            }
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(CHANNEL_ID, "Navegación Netheris", NotificationManager.IMPORTANCE_LOW)
            channel.description = "Ruta activa y navegación GPS"
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    private fun buildNotification(title: String, text: String) = NotificationCompat.Builder(this, CHANNEL_ID)
        .setSmallIcon(android.R.drawable.ic_dialog_map)
        .setContentTitle(title)
        .setContentText(text)
        .setOngoing(true)
        .setOnlyAlertOnce(true)
        .setContentIntent(
            PendingIntent.getActivity(
                this,
                0,
                Intent(this, MainActivity::class.java),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        )
        .addAction(
            android.R.drawable.ic_media_pause,
            "Detener",
            PendingIntent.getService(
                this,
                1,
                Intent(this, NavigationForegroundService::class.java).setAction(ACTION_STOP),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        )
        .build()

    private fun updateNotification(title: String, text: String) {
        getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, buildNotification(title, text))
    }

    private fun startLocationTracking() {
        val fine = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val coarse = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (!fine && !coarse) {
            updateNotification("Netheris GPS", "Falta permiso de ubicación")
            stopNavigation()
            return
        }

        listener?.let { runCatching { locationManager.removeUpdates(it) } }
        val l = LocationListener { location -> onLocation(location) }
        listener = l
        val provider = when {
            locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
            locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
            else -> null
        }
        if (provider == null) {
            updateNotification("Netheris GPS", "Activa la ubicación")
            return
        }
        runCatching {
            locationManager.requestLocationUpdates(provider, 1500L, 4f, l, Looper.getMainLooper())
            locationManager.getLastKnownLocation(provider)?.let(::onLocation)
        }
    }

    private fun onLocation(location: Location) {
        val dest = destination ?: return
        val here = P(location.latitude, location.longitude)
        val currentRoute = route
        if (currentRoute == null) {
            calculateRoute(here, dest)
            return
        }

        val idx = nearestIndex(here, currentRoute.points)
        val remaining = routeDistance(currentRoute.points, idx, currentRoute.points.lastIndex)
        val fraction = if (currentRoute.distance > 0) (remaining / currentRoute.distance).coerceIn(0.0, 1.0) else 0.0
        val eta = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(System.currentTimeMillis() + (currentRoute.duration * fraction * 1000).toLong()))
        val speed = if (location.hasSpeed()) location.speed * 3.6f else 0f

        var instruction = "Sigue la ruta"
        var next = ""
        if (currentRoute.steps.isNotEmpty()) {
            var s = stepIndex.coerceIn(0, currentRoute.steps.lastIndex)
            while (s < currentRoute.steps.lastIndex && currentRoute.steps[s].routeIndex <= idx + 2) s++
            stepIndex = s
            val step = currentRoute.steps[s]
            instruction = step.text
            val meters = if (step.routeIndex > idx) routeDistance(currentRoute.points, idx, step.routeIndex) else distance(here, step.point)
            next = formatDistance(meters)
        }

        NavStateStore.update(this, instruction, next, formatDistance(remaining), eta, "${max(0, speed.toInt())} km/h")
        updateNotification(if (next.isBlank()) instruction else "$instruction · $next", "$destinationLabel · ${formatDistance(remaining)} · ETA $eta")

        if (distance(here, dest) < 35f) {
            NavStateStore.update(this, "Llegaste al destino", "", "0 m", eta, "0 km/h")
            updateNotification("Llegaste al destino", destinationLabel)
            stopNavigation(clearState = false)
            return
        }

        val offRoute = distance(here, currentRoute.points[idx])
        val now = SystemClock.elapsedRealtime()
        if (offRoute > 90f && now - lastReroute > 15000L) {
            lastReroute = now
            route = null
            calculateRoute(here, dest)
        }
    }

    private fun calculateRoute(origin: P, dest: P) {
        updateNotification("Calculando ruta…", destinationLabel)
        Thread {
            try {
                val result = fetchRoute(origin, dest)
                if (result != null) {
                    route = result
                    stepIndex = if (result.steps.size > 1) 1 else 0
                } else {
                    updateNotification("Sin ruta disponible", destinationLabel)
                }
            } catch (_: Exception) {
                updateNotification("Error calculando ruta", destinationLabel)
            }
        }.start()
    }

    private fun fetchRoute(origin: P, dest: P): Route? {
        val url = "https://router.project-osrm.org/route/v1/driving/${origin.lon},${origin.lat};${dest.lon},${dest.lat}?overview=full&geometries=geojson&steps=true"
        val conn = URL(url).openConnection() as HttpURLConnection
        val text = try {
            conn.connectTimeout = 10000
            conn.readTimeout = 15000
            conn.setRequestProperty("User-Agent", "NetherisGPS/2.5 Android")
            if (conn.responseCode !in 200..299) return null
            conn.inputStream.bufferedReader().use { it.readText() }
        } finally { conn.disconnect() }

        val root = JSONObject(text)
        if (root.optString("code") != "Ok") return null
        val r = root.getJSONArray("routes").optJSONObject(0) ?: return null
        val coords = r.getJSONObject("geometry").getJSONArray("coordinates")
        val points = MutableList(coords.length()) { i ->
            val p = coords.getJSONArray(i)
            P(p.getDouble(1), p.getDouble(0))
        }
        val steps = mutableListOf<Step>()
        val legs = r.optJSONArray("legs")
        if (legs != null && legs.length() > 0) {
            val raw = legs.getJSONObject(0).optJSONArray("steps")
            if (raw != null) for (i in 0 until raw.length()) {
                val s = raw.getJSONObject(i)
                val m = s.optJSONObject("maneuver") ?: continue
                val loc = m.optJSONArray("location") ?: continue
                val point = P(loc.getDouble(1), loc.getDouble(0))
                steps += Step(instructionFor(s), point, nearestIndex(point, points))
            }
        }
        return Route(points, r.getDouble("distance"), r.getDouble("duration"), steps)
    }

    private fun instructionFor(step: JSONObject): String {
        val m = step.optJSONObject("maneuver") ?: JSONObject()
        val type = m.optString("type")
        val mod = m.optString("modifier")
        val road = step.optString("name")
        val base = when (mod) {
            "left", "sharp left", "slight left" -> "Gira a la izquierda"
            "right", "sharp right", "slight right" -> "Gira a la derecha"
            "uturn" -> "Haz un retorno"
            "straight" -> "Sigue recto"
            else -> when (type) {
                "depart" -> "Comienza la ruta"
                "arrive" -> "Llegaste al destino"
                "roundabout", "rotary" -> "Entra a la rotonda"
                "merge" -> "Incorpórate"
                "fork" -> "Toma la bifurcación"
                else -> "Continúa"
            }
        }
        return if (road.isNotBlank() && type != "arrive") "$base por $road" else base
    }

    private fun distance(a: P, b: P): Float {
        val result = FloatArray(1)
        Location.distanceBetween(a.lat, a.lon, b.lat, b.lon, result)
        return result[0]
    }

    private fun nearestIndex(point: P, route: List<P>): Int {
        if (route.isEmpty()) return 0
        var best = 0
        var bestD = Float.MAX_VALUE
        val stride = (route.size / 500).coerceAtLeast(1)
        var i = 0
        while (i < route.size) {
            val d = distance(point, route[i])
            if (d < bestD) { bestD = d; best = i }
            i += stride
        }
        val from = (best - stride * 2).coerceAtLeast(0)
        val to = (best + stride * 2).coerceAtMost(route.lastIndex)
        for (j in from..to) {
            val d = distance(point, route[j])
            if (d < bestD) { bestD = d; best = j }
        }
        return best
    }

    private fun routeDistance(route: List<P>, from: Int, to: Int): Float {
        if (route.size < 2) return 0f
        var total = 0f
        val start = from.coerceIn(0, route.lastIndex)
        val end = to.coerceIn(start, route.lastIndex)
        for (i in start until end) total += distance(route[i], route[i + 1])
        return total
    }

    private fun formatDistance(meters: Float): String = when {
        meters < 100f -> "${meters.toInt().coerceAtLeast(10)} m"
        meters < 1000f -> "${(meters / 10f).toInt() * 10} m"
        else -> String.format(Locale.getDefault(), "%.1f km", meters / 1000f)
    }

    private fun stopNavigation(clearState: Boolean = true) {
        listener?.let { runCatching { locationManager.removeUpdates(it) } }
        listener = null
        route = null
        if (clearState) NavStateStore.setActive(this, false)
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        listener?.let { runCatching { locationManager.removeUpdates(it) } }
        super.onDestroy()
    }
}
