package cl.netheris.gps

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.CancellationSignal
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.speech.tts.TextToSpeech
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import org.json.JSONArray
import org.json.JSONObject
import org.maplibre.android.MapLibre
import org.maplibre.android.annotations.Marker
import org.maplibre.android.annotations.MarkerOptions
import org.maplibre.android.annotations.Polyline
import org.maplibre.android.annotations.PolylineOptions
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.geometry.LatLngBounds
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapView
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.max

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        MapLibre.getInstance(this)
        setContent { NetherisGpsApp() }
    }
}

private val NetherisColors = darkColorScheme(
    primary = Color(0xFF6FE7FF),
    secondary = Color(0xFF9B8CFF),
    background = Color(0xFF07111D),
    surface = Color(0xFF0D1C2B),
    onPrimary = Color(0xFF00131A),
    onBackground = Color(0xFFEAF7FF),
    onSurface = Color(0xFFEAF7FF)
)

private const val MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty"
private const val PREFS_NAME = "netheris_gps"
private const val HOME_LAT = "home_lat"
private const val HOME_LON = "home_lon"
private const val FAVORITE_LAT = "favorite_lat"
private const val FAVORITE_LON = "favorite_lon"
private const val FAVORITE_LABEL = "favorite_label"
private const val RECENTS_JSON = "recents_json"
private const val OFF_ROUTE_METERS = 90f
private val Santiago = LatLng(-33.4489, -70.6693)

private data class SearchResult(val point: LatLng, val label: String)
private data class RouteStep(val instruction: String, val point: LatLng, val routeIndex: Int)
private data class RouteResult(
    val points: List<LatLng>,
    val distanceMeters: Double,
    val durationSeconds: Double,
    val steps: List<RouteStep>
)

private fun httpGet(url: String): String {
    val connection = URL(url).openConnection() as HttpURLConnection
    return try {
        connection.requestMethod = "GET"
        connection.connectTimeout = 10000
        connection.readTimeout = 15000
        connection.setRequestProperty("User-Agent", "NetherisGPS/1.8 Android")
        connection.setRequestProperty("Accept", "application/json")
        val code = connection.responseCode
        if (code !in 200..299) throw IllegalStateException("HTTP $code")
        connection.inputStream.bufferedReader().use { it.readText() }
    } finally {
        connection.disconnect()
    }
}

private fun searchPlaces(query: String): List<SearchResult> {
    val encoded = URLEncoder.encode("$query, Chile", StandardCharsets.UTF_8.toString())
    val url = "https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&countrycodes=cl&q=$encoded"
    val items = JSONArray(httpGet(url))
    val results = mutableListOf<SearchResult>()
    for (i in 0 until items.length()) {
        val item = items.getJSONObject(i)
        results.add(
            SearchResult(
                LatLng(item.getString("lat").toDouble(), item.getString("lon").toDouble()),
                item.optString("display_name", query)
            )
        )
    }
    return results
}

private fun instructionFor(step: JSONObject): String {
    val maneuver = step.optJSONObject("maneuver") ?: JSONObject()
    val type = maneuver.optString("type")
    val modifier = maneuver.optString("modifier")
    val road = step.optString("name")
    val direction = when (modifier) {
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
    return if (road.isNotBlank() && type != "arrive") "$direction por $road" else direction
}

private fun distanceMeters(a: LatLng, b: LatLng): Float {
    val result = FloatArray(1)
    Location.distanceBetween(a.latitude, a.longitude, b.latitude, b.longitude, result)
    return result[0]
}

private fun nearestRouteIndex(point: LatLng, route: List<LatLng>): Int {
    if (route.isEmpty()) return 0
    var bestIndex = 0
    var bestDistance = Float.MAX_VALUE
    val stride = (route.size / 500).coerceAtLeast(1)
    var i = 0
    while (i < route.size) {
        val d = distanceMeters(point, route[i])
        if (d < bestDistance) {
            bestDistance = d
            bestIndex = i
        }
        i += stride
    }
    val from = (bestIndex - stride * 2).coerceAtLeast(0)
    val to = (bestIndex + stride * 2).coerceAtMost(route.lastIndex)
    for (j in from..to) {
        val d = distanceMeters(point, route[j])
        if (d < bestDistance) {
            bestDistance = d
            bestIndex = j
        }
    }
    return bestIndex
}

private fun routeDistance(route: List<LatLng>, fromIndex: Int, toIndex: Int): Float {
    if (route.size < 2) return 0f
    val start = fromIndex.coerceIn(0, route.lastIndex)
    val end = toIndex.coerceIn(start, route.lastIndex)
    var total = 0f
    for (i in start until end) total += distanceMeters(route[i], route[i + 1])
    return total
}

private fun parseRoute(route: JSONObject): RouteResult {
    val coordinates = route.getJSONObject("geometry").getJSONArray("coordinates")
    val points = ArrayList<LatLng>(coordinates.length())
    for (i in 0 until coordinates.length()) {
        val pair = coordinates.getJSONArray(i)
        points.add(LatLng(pair.getDouble(1), pair.getDouble(0)))
    }
    val steps = mutableListOf<RouteStep>()
    val legs = route.optJSONArray("legs")
    if (legs != null && legs.length() > 0) {
        val rawSteps = legs.getJSONObject(0).optJSONArray("steps")
        if (rawSteps != null) {
            for (i in 0 until rawSteps.length()) {
                val step = rawSteps.getJSONObject(i)
                val location = step.optJSONObject("maneuver")?.optJSONArray("location") ?: continue
                if (location.length() >= 2) {
                    val point = LatLng(location.getDouble(1), location.getDouble(0))
                    steps.add(RouteStep(instructionFor(step), point, nearestRouteIndex(point, points)))
                }
            }
        }
    }
    return RouteResult(points, route.getDouble("distance"), route.getDouble("duration"), steps)
}

private fun fetchRoutes(origin: LatLng, destination: LatLng): List<RouteResult> {
    val url = "https://router.project-osrm.org/route/v1/driving/" +
        "${origin.longitude},${origin.latitude};${destination.longitude},${destination.latitude}" +
        "?overview=full&geometries=geojson&steps=true&alternatives=2"
    val root = JSONObject(httpGet(url))
    if (root.optString("code") != "Ok") return emptyList()
    val routes = root.optJSONArray("routes") ?: return emptyList()
    val result = mutableListOf<RouteResult>()
    for (i in 0 until routes.length()) result.add(parseRoute(routes.getJSONObject(i)))
    return result
}

private fun distanceToRoute(point: LatLng, route: List<LatLng>): Float {
    if (route.isEmpty()) return Float.MAX_VALUE
    val index = nearestRouteIndex(point, route)
    return distanceMeters(point, route[index])
}

private fun formatDistance(meters: Float): String = when {
    meters < 100f -> "${meters.toInt().coerceAtLeast(10)} m"
    meters < 1000f -> "${(meters / 10f).toInt() * 10} m"
    else -> String.format(Locale.getDefault(), "%.1f km", meters / 1000f)
}

private fun bearingBetween(a: LatLng, b: LatLng): Float {
    val start = Location("start").apply { latitude = a.latitude; longitude = a.longitude }
    val end = Location("end").apply { latitude = b.latitude; longitude = b.longitude }
    return start.bearingTo(end)
}

private fun saveRecent(prefs: android.content.SharedPreferences, result: SearchResult) {
    val existing = loadRecents(prefs).filterNot {
        distanceMeters(it.point, result.point) < 25f || it.label == result.label
    }.toMutableList()
    existing.add(0, result)
    val array = JSONArray()
    existing.take(4).forEach {
        array.put(JSONObject().put("label", it.label).put("lat", it.point.latitude).put("lon", it.point.longitude))
    }
    prefs.edit().putString(RECENTS_JSON, array.toString()).apply()
}

private fun loadRecents(prefs: android.content.SharedPreferences): List<SearchResult> {
    return try {
        val array = JSONArray(prefs.getString(RECENTS_JSON, "[]") ?: "[]")
        List(array.length()) { i ->
            val o = array.getJSONObject(i)
            SearchResult(LatLng(o.getDouble("lat"), o.getDouble("lon")), o.getString("label"))
        }
    } catch (_: Exception) { emptyList() }
}

@Composable
fun NetherisGpsApp() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE) }
    val mainHandler = remember { Handler(Looper.getMainLooper()) }
    val locationManager = remember { context.getSystemService(Context.LOCATION_SERVICE) as LocationManager }

    var map by remember { mutableStateOf<MapLibreMap?>(null) }
    var status by remember { mutableStateOf("Cargando mapa…") }
    var searchText by remember { mutableStateOf("") }
    var searchResults by remember { mutableStateOf<List<SearchResult>>(emptyList()) }
    var recents by remember { mutableStateOf(loadRecents(prefs)) }
    var nextInstruction by remember { mutableStateOf("") }
    var nextDistance by remember { mutableStateOf("") }
    var remainingInfo by remember { mutableStateOf("") }
    var speedInfo by remember { mutableStateOf("0 km/h") }
    var etaInfo by remember { mutableStateOf("--:--") }
    var lastLocation by remember { mutableStateOf<LatLng?>(null) }
    var destination by remember { mutableStateOf<SearchResult?>(null) }
    var routeOptions by remember { mutableStateOf<List<RouteResult>>(emptyList()) }
    var selectedRouteIndex by remember { mutableStateOf(0) }
    var activeRoute by remember { mutableStateOf<RouteResult?>(null) }
    var navigationActive by remember { mutableStateOf(false) }
    var demoActive by remember { mutableStateOf(false) }
    var voiceEnabled by remember { mutableStateOf(true) }
    var currentStepIndex by remember { mutableStateOf(0) }
    var lastSpokenFarStep by remember { mutableStateOf(-1) }
    var lastSpokenNearStep by remember { mutableStateOf(-1) }
    var lastRerouteAt by remember { mutableStateOf(0L) }
    var locationMarker by remember { mutableStateOf<Marker?>(null) }
    var homeMarker by remember { mutableStateOf<Marker?>(null) }
    var favoriteMarker by remember { mutableStateOf<Marker?>(null) }
    var destinationMarker by remember { mutableStateOf<Marker?>(null) }
    var routePolyline by remember { mutableStateOf<Polyline?>(null) }
    var trackingListener by remember { mutableStateOf<LocationListener?>(null) }
    var demoRunnable by remember { mutableStateOf<Runnable?>(null) }

    var ttsReady by remember { mutableStateOf(false) }
    val tts = remember { TextToSpeech(context) { if (it == TextToSpeech.SUCCESS) ttsReady = true } }

    fun speak(text: String) {
        if (!voiceEnabled || !ttsReady || text.isBlank()) return
        tts.language = Locale("es", "CL")
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "netheris_nav")
    }

    fun showLocation(latLng: LatLng, moveCamera: Boolean = true, bearing: Float? = null) {
        val readyMap = map ?: return
        locationMarker?.let { readyMap.removeMarker(it) }
        locationMarker = readyMap.addMarker(MarkerOptions().position(latLng).title(if (demoActive) "Demo" else "Mi ubicación"))
        if (moveCamera) {
            val builder = CameraPosition.Builder().target(latLng).zoom(if (navigationActive || demoActive) 17.2 else 16.5)
            if (navigationActive || demoActive) {
                builder.tilt(48.0)
                if (bearing != null && !bearing.isNaN()) builder.bearing(bearing.toDouble())
            }
            readyMap.animateCamera(CameraUpdateFactory.newCameraPosition(builder.build()), 350)
        }
        lastLocation = latLng
    }

    fun showHome(latLng: LatLng, moveCamera: Boolean = true) {
        val readyMap = map ?: return
        homeMarker?.let { readyMap.removeMarker(it) }
        homeMarker = readyMap.addMarker(MarkerOptions().position(latLng).title("Casa · Netheris"))
        if (moveCamera) readyMap.cameraPosition = CameraPosition.Builder().target(latLng).zoom(16.5).build()
    }

    fun showFavorite(latLng: LatLng, label: String, moveCamera: Boolean = true) {
        val readyMap = map ?: return
        favoriteMarker?.let { readyMap.removeMarker(it) }
        favoriteMarker = readyMap.addMarker(MarkerOptions().position(latLng).title("⭐ $label"))
        if (moveCamera) readyMap.cameraPosition = CameraPosition.Builder().target(latLng).zoom(16.5).build()
    }

    fun selectDestination(result: SearchResult, moveCamera: Boolean = true) {
        val readyMap = map ?: return
        destinationMarker?.let { readyMap.removeMarker(it) }
        destinationMarker = readyMap.addMarker(MarkerOptions().position(result.point).title(result.label))
        destination = result
        searchResults = emptyList()
        routeOptions = emptyList()
        activeRoute = null
        selectedRouteIndex = 0
        saveRecent(prefs, result)
        recents = loadRecents(prefs)
        if (moveCamera) readyMap.cameraPosition = CameraPosition.Builder().target(result.point).zoom(16.0).build()
        status = "Destino seleccionado"
    }

    fun updateProgress(point: LatLng, speedKmh: Float) {
        val route = activeRoute ?: return
        if (route.points.isEmpty()) return
        val routeIndex = nearestRouteIndex(point, route.points)
        val remainingMeters = routeDistance(route.points, routeIndex, route.points.lastIndex)
        val fraction = if (route.distanceMeters > 0.0) (remainingMeters / route.distanceMeters).coerceIn(0.0, 1.0) else 0.0
        val secondsRemaining = route.durationSeconds * fraction
        etaInfo = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(System.currentTimeMillis() + (secondsRemaining * 1000).toLong()))
        remainingInfo = formatDistance(remainingMeters)
        speedInfo = "${speedKmh.toInt().coerceAtLeast(0)} km/h"
        if (route.steps.isEmpty()) return
        var index = currentStepIndex.coerceIn(0, route.steps.lastIndex)
        while (index < route.steps.lastIndex && route.steps[index].routeIndex <= routeIndex + 2) index++
        currentStepIndex = index
        val step = route.steps[index]
        val toManeuver = if (step.routeIndex > routeIndex) routeDistance(route.points, routeIndex, step.routeIndex) else distanceMeters(point, step.point)
        nextInstruction = step.instruction
        nextDistance = formatDistance(toManeuver)
        if (index != lastSpokenFarStep && toManeuver in 120f..450f) {
            speak("En ${formatDistance(toManeuver)}, ${step.instruction.lowercase(Locale.getDefault())}")
            lastSpokenFarStep = index
        }
        if (index != lastSpokenNearStep && toManeuver < 70f) {
            speak(step.instruction)
            lastSpokenNearStep = index
        }
    }

    fun drawRoute(result: RouteResult, origin: LatLng, dest: LatLng, fitBounds: Boolean = true) {
        val readyMap = map ?: return
        routePolyline?.let { readyMap.removePolyline(it) }
        routePolyline = readyMap.addPolyline(PolylineOptions().addAll(result.points).color(0xFF30D5FF.toInt()).width(7f))
        activeRoute = result
        currentStepIndex = if (result.steps.size > 1) 1 else 0
        lastSpokenFarStep = -1
        lastSpokenNearStep = -1
        if (fitBounds) {
            val boundsBuilder = LatLngBounds.Builder().include(origin).include(dest)
            result.points.forEach { boundsBuilder.include(it) }
            readyMap.animateCamera(CameraUpdateFactory.newLatLngBounds(boundsBuilder.build(), 80), 800)
        }
        remainingInfo = String.format(Locale.getDefault(), "%.1f km", result.distanceMeters / 1000.0)
        etaInfo = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(System.currentTimeMillis() + (result.durationSeconds * 1000).toLong()))
        lastLocation?.let { updateProgress(it, 0f) }
        status = "Ruta ${selectedRouteIndex + 1}/${routeOptions.size.coerceAtLeast(1)} lista"
    }

    fun requestLocation(onResult: (LatLng?) -> Unit = {}) {
        val hasFine = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val hasCoarse = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (!hasFine && !hasCoarse) { status = "Necesito permiso de ubicación"; onResult(null); return }
        val callback: (Location?) -> Unit = { location ->
            if (location != null) {
                val p = LatLng(location.latitude, location.longitude)
                showLocation(p)
                status = "Ubicación encontrada"
                onResult(p)
            } else { status = "Sin ubicación todavía"; onResult(null) }
        }
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val provider = when {
                    locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
                    locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
                    else -> null
                }
                if (provider == null) { status = "Activa la ubicación"; onResult(null); return }
                locationManager.getCurrentLocation(provider, CancellationSignal(), ContextCompat.getMainExecutor(context), callback)
            } else callback(locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER) ?: locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER))
        } catch (_: SecurityException) { status = "Sin permiso GPS"; onResult(null) }
    }

    fun stopNavigation() {
        trackingListener?.let { try { locationManager.removeUpdates(it) } catch (_: Exception) {} }
        trackingListener = null
        demoRunnable?.let { mainHandler.removeCallbacks(it) }
        demoRunnable = null
        navigationActive = false
        demoActive = false
        status = "Navegación detenida"
    }

    fun calculateRoutes() {
        val dest = destination ?: run { status = "Primero selecciona destino"; return }
        fun build(origin: LatLng) {
            status = "Calculando rutas…"
            Thread {
                try {
                    val routes = fetchRoutes(origin, dest.point)
                    mainHandler.post {
                        if (routes.isEmpty()) status = "No pude calcular ruta"
                        else {
                            routeOptions = routes
                            selectedRouteIndex = 0
                            drawRoute(routes[0], origin, dest.point)
                        }
                    }
                } catch (_: Exception) { mainHandler.post { status = "Error calculando ruta" } }
            }.start()
        }
        lastLocation?.let(::build) ?: requestLocation { it?.let(::build) }
    }

    fun cycleAlternative() {
        if (routeOptions.size <= 1) { status = "No hay ruta alternativa"; return }
        val origin = lastLocation ?: return
        val dest = destination ?: return
        selectedRouteIndex = (selectedRouteIndex + 1) % routeOptions.size
        drawRoute(routeOptions[selectedRouteIndex], origin, dest.point)
    }

    fun recalculateFrom(origin: LatLng) {
        val dest = destination ?: return
        status = "Recalculando…"
        lastRerouteAt = SystemClock.elapsedRealtime()
        speak("Ruta desviada. Recalculando")
        Thread {
            try {
                val routes = fetchRoutes(origin, dest.point)
                mainHandler.post {
                    if (routes.isNotEmpty()) {
                        routeOptions = routes
                        selectedRouteIndex = 0
                        drawRoute(routes[0], origin, dest.point, false)
                    } else status = "No pude recalcular"
                }
            } catch (_: Exception) { mainHandler.post { status = "Error recalculando" } }
        }.start()
    }

    fun startNavigation() {
        val dest = destination ?: run { status = "Selecciona destino"; return }
        val route = activeRoute ?: run { status = "Calcula una ruta"; return }
        val hasPermission = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (!hasPermission) { status = "Necesito permiso GPS"; return }
        stopNavigation(); navigationActive = true; status = "Navegando"; speak("Navegación iniciada")
        val listener = LocationListener { location ->
            val point = LatLng(location.latitude, location.longitude)
            val speed = if (location.hasSpeed()) location.speed * 3.6f else 0f
            showLocation(point, true, if (location.hasBearing()) location.bearing else null)
            updateProgress(point, speed)
            val current = activeRoute
            if (current != null && distanceToRoute(point, current.points) > OFF_ROUTE_METERS && SystemClock.elapsedRealtime() - lastRerouteAt > 15000L) recalculateFrom(point)
            else status = "Navegando"
            if (distanceMeters(point, dest.point) < 35f) {
                remainingInfo = "0 m"; nextInstruction = "Llegaste al destino 🎉"; nextDistance = ""; speak("Llegaste al destino"); stopNavigation(); status = "Destino alcanzado"
            }
        }
        trackingListener = listener
        try {
            val provider = if (locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) LocationManager.GPS_PROVIDER else LocationManager.NETWORK_PROVIDER
            locationManager.requestLocationUpdates(provider, 1500L, 4f, listener, Looper.getMainLooper())
        } catch (_: Exception) { navigationActive = false; status = "No pude iniciar navegación" }
    }

    fun startDemo() {
        val route = activeRoute ?: run { status = "Calcula una ruta"; return }
        if (route.points.size < 2) return
        stopNavigation(); demoActive = true; navigationActive = true; status = "DEMO navegando"; speak("Modo demostración iniciado")
        val stride = max(1, route.points.size / 180)
        var index = 0
        lateinit var runner: Runnable
        runner = Runnable {
            if (!demoActive) return@Runnable
            val current = activeRoute ?: return@Runnable
            if (index >= current.points.lastIndex) {
                showLocation(current.points.last(), true); remainingInfo = "0 m"; nextInstruction = "Llegaste al destino 🎉"; nextDistance = ""; speak("Llegaste al destino"); demoActive = false; navigationActive = false; status = "DEMO finalizada"; return@Runnable
            }
            val point = current.points[index]
            val next = (index + stride).coerceAtMost(current.points.lastIndex)
            showLocation(point, true, bearingBetween(point, current.points[next]))
            updateProgress(point, 42f)
            index = next
            mainHandler.postDelayed(runner, 650L)
        }
        demoRunnable = runner
        mainHandler.post(runner)
    }

    DisposableEffect(Unit) {
        onDispose {
            trackingListener?.let { try { locationManager.removeUpdates(it) } catch (_: Exception) {} }
            demoRunnable?.let { mainHandler.removeCallbacks(it) }
            tts.stop(); tts.shutdown()
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { p ->
        if (p.values.any { it }) requestLocation() else status = "Permiso rechazado"
    }
    fun ensureLocation() {
        val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (granted) requestLocation() else permissionLauncher.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION))
    }

    fun findDestination() {
        val query = searchText.trim()
        if (query.isEmpty()) { status = "Escribe un destino"; return }
        status = "Buscando…"
        Thread {
            try {
                val results = searchPlaces(query)
                mainHandler.post { searchResults = results; status = if (results.isEmpty()) "Sin resultados" else "${results.size} resultados" }
            } catch (_: Exception) { mainHandler.post { status = "Error buscando" } }
        }.start()
    }

    MaterialTheme(colorScheme = NetherisColors) {
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            Column(modifier = Modifier.fillMaxSize().padding(horizontal = 10.dp, vertical = 7.dp)) {
                Text("NETHERIS GPS", fontSize = 22.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                Text("V1.8 · $status", color = Color(0xFF9EB8C8), fontSize = 12.sp)

                if (activeRoute != null) {
                    Spacer(Modifier.height(3.dp))
                    Surface(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp), color = Color(0xFF102334)) {
                        Row(modifier = Modifier.fillMaxWidth().padding(8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Restante $remainingInfo", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                            Text("ETA $etaInfo", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                            Text(speedInfo, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        }
                    }
                }
                if (nextInstruction.isNotEmpty()) {
                    Spacer(Modifier.height(3.dp))
                    Surface(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp), color = Color(0xFF173247)) {
                        Row(modifier = Modifier.fillMaxWidth().padding(8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(nextInstruction, color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold, modifier = Modifier.fillMaxWidth(0.76f), maxLines = 2, overflow = TextOverflow.Ellipsis)
                            Text(nextDistance, color = MaterialTheme.colorScheme.primary, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }

                Spacer(Modifier.height(4.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                    OutlinedTextField(value = searchText, onValueChange = { searchText = it }, modifier = Modifier.fillMaxWidth(0.72f), singleLine = true, label = { Text("Destino") })
                    Button(onClick = { findDestination() }, colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary, contentColor = Color(0xFF0A0717))) { Text("Buscar") }
                }

                if (searchResults.isNotEmpty()) {
                    searchResults.take(3).forEach { result ->
                        TextButton(onClick = { selectDestination(result) }, modifier = Modifier.fillMaxWidth()) {
                            Text("📌 ${result.label}", maxLines = 1, overflow = TextOverflow.Ellipsis, color = Color.White)
                        }
                    }
                } else if (destination == null && recents.isNotEmpty()) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        recents.take(2).forEach { recent ->
                            TextButton(onClick = { selectDestination(recent) }) { Text("🕘 ${recent.label.substringBefore(",").take(18)}", color = Color(0xFFB6CADA), fontSize = 12.sp) }
                        }
                    }
                }

                Spacer(Modifier.height(3.dp))
                Box(modifier = Modifier.fillMaxWidth().height(if (activeRoute != null) 220.dp else if (searchResults.isNotEmpty()) 220.dp else 300.dp)) {
                    NetherisMap(
                        modifier = Modifier.fillMaxSize(),
                        onMapReady = { readyMap ->
                            map = readyMap
                            status = "Mapa listo · mantén pulsado para destino"
                            if (prefs.contains(HOME_LAT) && prefs.contains(HOME_LON)) showHome(LatLng(prefs.getLong(HOME_LAT, 0L).let(Double::fromBits), prefs.getLong(HOME_LON, 0L).let(Double::fromBits)), false)
                            if (prefs.contains(FAVORITE_LAT) && prefs.contains(FAVORITE_LON)) showFavorite(LatLng(prefs.getLong(FAVORITE_LAT, 0L).let(Double::fromBits), prefs.getLong(FAVORITE_LON, 0L).let(Double::fromBits)), prefs.getString(FAVORITE_LABEL, "Favorito") ?: "Favorito", false)
                        },
                        onLongPress = { point -> selectDestination(SearchResult(point, "Punto en mapa"), false) }
                    )
                }

                Spacer(Modifier.height(4.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    Button(onClick = { ensureLocation() }, colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary, contentColor = MaterialTheme.colorScheme.onPrimary)) { Text("📍") }
                    Button(onClick = { calculateRoutes() }, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF21C7A8), contentColor = Color(0xFF001A16))) { Text("🚗 Ruta") }
                    Button(onClick = { cycleAlternative() }, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF446B8D), contentColor = Color.White)) { Text("↔ Alt") }
                    Button(onClick = { if (navigationActive && !demoActive) stopNavigation() else startNavigation() }, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF305B8E), contentColor = Color.White)) { Text(if (navigationActive && !demoActive) "⏹" else "▶ Nav") }
                }

                Spacer(Modifier.height(3.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    Button(onClick = { if (demoActive) stopNavigation() else startDemo() }, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6A4C93), contentColor = Color.White)) { Text(if (demoActive) "⏹ Demo" else "▶ Demo") }
                    Button(onClick = { voiceEnabled = !voiceEnabled; if (!voiceEnabled) tts.stop() }, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF24384A), contentColor = Color.White)) { Text(if (voiceEnabled) "🔊" else "🔇") }
                    Button(onClick = {
                        val d = destination ?: run { status = "Selecciona destino"; return@Button }
                        prefs.edit().putLong(FAVORITE_LAT, d.point.latitude.toBits()).putLong(FAVORITE_LON, d.point.longitude.toBits()).putString(FAVORITE_LABEL, d.label.substringBefore(",")).apply()
                        showFavorite(d.point, d.label.substringBefore(","), false); status = "Favorito guardado"
                    }, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF705A22), contentColor = Color.White)) { Text("⭐ Guardar") }
                    Button(onClick = {
                        if (prefs.contains(FAVORITE_LAT)) selectDestination(SearchResult(LatLng(prefs.getLong(FAVORITE_LAT, 0L).let(Double::fromBits), prefs.getLong(FAVORITE_LON, 0L).let(Double::fromBits)), prefs.getString(FAVORITE_LABEL, "Favorito") ?: "Favorito")) else status = "Sin favorito"
                    }, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF24384A), contentColor = Color.White)) { Text("⭐ Ir") }
                }

                Spacer(Modifier.height(3.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    Button(onClick = {
                        val save: (LatLng) -> Unit = { p -> prefs.edit().putLong(HOME_LAT, p.latitude.toBits()).putLong(HOME_LON, p.longitude.toBits()).apply(); showHome(p, false); status = "Casa guardada" }
                        lastLocation?.let(save) ?: requestLocation { it?.let(save) }
                    }, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF24384A), contentColor = Color.White)) { Text("🏠 Guardar") }
                    Button(onClick = {
                        if (prefs.contains(HOME_LAT)) selectDestination(SearchResult(LatLng(prefs.getLong(HOME_LAT, 0L).let(Double::fromBits), prefs.getLong(HOME_LON, 0L).let(Double::fromBits)), "Casa · Netheris")) else status = "Casa no guardada"
                    }, colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary, contentColor = Color(0xFF0A0717))) { Text("🏡 Casa") }
                    Button(onClick = {
                        stopNavigation(); routePolyline?.let { map?.removePolyline(it) }; routePolyline = null; destinationMarker?.let { map?.removeMarker(it) }; destinationMarker = null; destination = null; activeRoute = null; routeOptions = emptyList(); searchResults = emptyList(); nextInstruction = ""; nextDistance = ""; remainingInfo = ""; speedInfo = "0 km/h"; etaInfo = "--:--"; status = "Ruta limpiada"
                    }, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF24384A), contentColor = Color.White)) { Text("Limpiar") }
                }
            }
        }
    }
}

@Composable
private fun NetherisMap(
    modifier: Modifier = Modifier,
    onMapReady: (MapLibreMap) -> Unit,
    onLongPress: (LatLng) -> Unit
) {
    val context = LocalContext.current
    val mapView = remember { MapView(context) }
    AndroidView(
        modifier = modifier,
        factory = {
            mapView.apply {
                onCreate(null); onStart(); onResume()
                getMapAsync { readyMap ->
                    readyMap.setStyle(MAP_STYLE) {
                        readyMap.cameraPosition = CameraPosition.Builder().target(Santiago).zoom(12.5).build()
                        readyMap.addOnMapLongClickListener { point -> onLongPress(point); true }
                        onMapReady(readyMap)
                    }
                }
            }
        }
    )
    DisposableEffect(mapView) {
        onDispose { mapView.onPause(); mapView.onStop(); mapView.onDestroy() }
    }
}
