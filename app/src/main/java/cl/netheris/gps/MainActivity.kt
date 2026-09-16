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
private const val OFF_ROUTE_METERS = 90f
private val Santiago = LatLng(-33.4489, -70.6693)

private data class SearchResult(val point: LatLng, val label: String)
private data class RouteStep(
    val instruction: String,
    val distanceMeters: Double,
    val point: LatLng,
    val routeIndex: Int
)
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
        connection.setRequestProperty("User-Agent", "NetherisGPS/1.5 Android")
        connection.setRequestProperty("Accept", "application/json")
        val code = connection.responseCode
        if (code !in 200..299) throw IllegalStateException("HTTP $code")
        connection.inputStream.bufferedReader().use { it.readText() }
    } finally {
        connection.disconnect()
    }
}

private fun searchPlace(query: String): SearchResult? {
    val encoded = URLEncoder.encode("$query, Chile", StandardCharsets.UTF_8.toString())
    val url = "https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=cl&q=$encoded"
    val items = JSONArray(httpGet(url))
    if (items.length() == 0) return null
    val item = items.getJSONObject(0)
    return SearchResult(
        LatLng(item.getString("lat").toDouble(), item.getString("lon").toDouble()),
        item.optString("display_name", query)
    )
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

private fun fetchRoute(origin: LatLng, destination: LatLng): RouteResult? {
    val url = "https://router.project-osrm.org/route/v1/driving/" +
        "${origin.longitude},${origin.latitude};${destination.longitude},${destination.latitude}" +
        "?overview=full&geometries=geojson&steps=true"
    val root = JSONObject(httpGet(url))
    if (root.optString("code") != "Ok") return null
    val routes = root.optJSONArray("routes") ?: return null
    if (routes.length() == 0) return null
    val route = routes.getJSONObject(0)
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
                val location = step.optJSONObject("maneuver")?.optJSONArray("location")
                if (location != null && location.length() >= 2) {
                    val point = LatLng(location.getDouble(1), location.getDouble(0))
                    steps.add(
                        RouteStep(
                            instructionFor(step),
                            step.optDouble("distance", 0.0),
                            point,
                            nearestRouteIndex(point, points)
                        )
                    )
                }
            }
        }
    }
    return RouteResult(points, route.getDouble("distance"), route.getDouble("duration"), steps)
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
    val start = Location("start").apply {
        latitude = a.latitude
        longitude = a.longitude
    }
    val end = Location("end").apply {
        latitude = b.latitude
        longitude = b.longitude
    }
    return start.bearingTo(end)
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
    var routeInfo by remember { mutableStateOf("") }
    var nextInstruction by remember { mutableStateOf("") }
    var nextDistance by remember { mutableStateOf("") }
    var remainingInfo by remember { mutableStateOf("") }
    var speedInfo by remember { mutableStateOf("0 km/h") }
    var etaInfo by remember { mutableStateOf("--:--") }
    var lastLocation by remember { mutableStateOf<LatLng?>(null) }
    var destination by remember { mutableStateOf<SearchResult?>(null) }
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
    var destinationMarker by remember { mutableStateOf<Marker?>(null) }
    var routePolyline by remember { mutableStateOf<Polyline?>(null) }
    var trackingListener by remember { mutableStateOf<LocationListener?>(null) }
    var demoRunnable by remember { mutableStateOf<Runnable?>(null) }

    var ttsReady by remember { mutableStateOf(false) }
    val tts = remember {
        TextToSpeech(context) { result ->
            if (result == TextToSpeech.SUCCESS) ttsReady = true
        }
    }

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

    fun showDestination(result: SearchResult) {
        val readyMap = map ?: return
        destinationMarker?.let { readyMap.removeMarker(it) }
        destinationMarker = readyMap.addMarker(MarkerOptions().position(result.point).title("Destino"))
        destination = result
        readyMap.cameraPosition = CameraPosition.Builder().target(result.point).zoom(16.0).build()
    }

    fun updateProgress(point: LatLng, speedKmh: Float) {
        val route = activeRoute ?: return
        if (route.points.isEmpty()) return
        val routeIndex = nearestRouteIndex(point, route.points)
        val remainingMeters = routeDistance(route.points, routeIndex, route.points.lastIndex)
        val fraction = if (route.distanceMeters > 0.0) (remainingMeters / route.distanceMeters).coerceIn(0.0, 1.0) else 0.0
        val secondsRemaining = route.durationSeconds * fraction
        val etaMillis = System.currentTimeMillis() + (secondsRemaining * 1000.0).toLong()
        val formatter = SimpleDateFormat("HH:mm", Locale.getDefault())
        etaInfo = formatter.format(Date(etaMillis))
        remainingInfo = formatDistance(remainingMeters)
        speedInfo = "${speedKmh.toInt().coerceAtLeast(0)} km/h"

        if (route.steps.isEmpty()) return
        var index = currentStepIndex.coerceIn(0, route.steps.lastIndex)
        while (index < route.steps.lastIndex && route.steps[index].routeIndex <= routeIndex + 2) index++
        if (index != currentStepIndex) currentStepIndex = index
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
        routeInfo = String.format(Locale.getDefault(), "%.1f km · %.0f min", result.distanceMeters / 1000.0, result.durationSeconds / 60.0)
        remainingInfo = String.format(Locale.getDefault(), "%.1f km", result.distanceMeters / 1000.0)
        val etaMillis = System.currentTimeMillis() + (result.durationSeconds * 1000.0).toLong()
        etaInfo = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(etaMillis))
        lastLocation?.let { updateProgress(it, 0f) }
        status = if (navigationActive) "Navegando" else "Ruta calculada"
    }

    fun requestLocation(onResult: (LatLng?) -> Unit = {}) {
        val hasFine = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val hasCoarse = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (!hasFine && !hasCoarse) {
            status = "Necesito permiso de ubicación"
            onResult(null)
            return
        }
        val handleLocation: (Location?) -> Unit = { location ->
            if (location != null) {
                val point = LatLng(location.latitude, location.longitude)
                showLocation(point)
                status = "Ubicación encontrada"
                onResult(point)
            } else {
                status = "No pude obtener una ubicación todavía"
                onResult(null)
            }
        }
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val provider = when {
                    locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
                    locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
                    else -> null
                }
                if (provider == null) {
                    status = "Activa la ubicación del teléfono"
                    onResult(null)
                    return
                }
                status = "Buscando ubicación…"
                locationManager.getCurrentLocation(provider, CancellationSignal(), ContextCompat.getMainExecutor(context), handleLocation)
            } else {
                handleLocation(locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER) ?: locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER))
            }
        } catch (_: SecurityException) {
            status = "No tengo permiso para acceder al GPS"
            onResult(null)
        }
    }

    fun stopNavigation() {
        trackingListener?.let { try { locationManager.removeUpdates(it) } catch (_: Exception) { } }
        trackingListener = null
        demoRunnable?.let { mainHandler.removeCallbacks(it) }
        demoRunnable = null
        navigationActive = false
        demoActive = false
        status = "Navegación detenida"
    }

    fun recalculateFrom(origin: LatLng, fitBounds: Boolean = false) {
        val dest = destination ?: return
        status = "Recalculando…"
        lastRerouteAt = SystemClock.elapsedRealtime()
        speak("Ruta desviada. Recalculando")
        Thread {
            try {
                val route = fetchRoute(origin, dest.point)
                mainHandler.post {
                    if (route != null) drawRoute(route, origin, dest.point, fitBounds) else status = "No pude recalcular"
                }
            } catch (_: Exception) {
                mainHandler.post { status = "Error recalculando" }
            }
        }.start()
    }

    fun startNavigation() {
        val dest = destination
        val route = activeRoute
        if (dest == null || route == null) {
            status = "Primero calcula una ruta"
            return
        }
        val hasPermission = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (!hasPermission) {
            status = "Necesito permiso de ubicación"
            return
        }
        stopNavigation()
        navigationActive = true
        status = "Navegando"
        currentStepIndex = if (route.steps.size > 1) 1 else 0
        lastSpokenFarStep = -1
        lastSpokenNearStep = -1
        speak("Navegación iniciada")

        val listener = LocationListener { location ->
            val point = LatLng(location.latitude, location.longitude)
            val speedKmh = if (location.hasSpeed()) location.speed * 3.6f else 0f
            showLocation(point, true, if (location.hasBearing()) location.bearing else null)
            updateProgress(point, speedKmh)
            val currentRoute = activeRoute
            if (currentRoute != null) {
                val offRoute = distanceToRoute(point, currentRoute.points)
                val now = SystemClock.elapsedRealtime()
                if (offRoute > OFF_ROUTE_METERS && now - lastRerouteAt > 15000L) recalculateFrom(point, false)
                else status = "Navegando"
            }
            val remaining = distanceMeters(point, dest.point)
            if (remaining < 35f) {
                nextInstruction = "Llegaste al destino 🎉"
                nextDistance = ""
                remainingInfo = "0 m"
                status = "Destino alcanzado"
                speak("Llegaste al destino")
                stopNavigation()
            }
        }
        trackingListener = listener
        try {
            val provider = when {
                locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
                locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
                else -> null
            }
            if (provider == null) {
                navigationActive = false
                status = "Activa la ubicación del teléfono"
                return
            }
            locationManager.requestLocationUpdates(provider, 1500L, 4f, listener, Looper.getMainLooper())
            lastLocation?.let { showLocation(it, true) }
        } catch (_: SecurityException) {
            navigationActive = false
            status = "No tengo permiso para navegar"
        }
    }

    fun startDemo() {
        val route = activeRoute
        if (route == null || route.points.size < 2) {
            status = "Primero calcula una ruta"
            return
        }
        stopNavigation()
        demoActive = true
        navigationActive = true
        status = "DEMO navegando"
        currentStepIndex = if (route.steps.size > 1) 1 else 0
        lastSpokenFarStep = -1
        lastSpokenNearStep = -1
        speak("Modo demostración iniciado")
        val stride = max(1, route.points.size / 180)
        var index = 0
        lateinit var runner: Runnable
        runner = Runnable {
            if (!demoActive || activeRoute == null) return@Runnable
            val currentRoute = activeRoute ?: return@Runnable
            if (index >= currentRoute.points.lastIndex) {
                val end = currentRoute.points.last()
                showLocation(end, true)
                remainingInfo = "0 m"
                nextInstruction = "Llegaste al destino 🎉"
                nextDistance = ""
                status = "DEMO finalizada"
                speak("Llegaste al destino")
                navigationActive = false
                demoActive = false
                return@Runnable
            }
            val point = currentRoute.points[index]
            val nextIndex = (index + stride).coerceAtMost(currentRoute.points.lastIndex)
            val bearing = bearingBetween(point, currentRoute.points[nextIndex])
            val demoSpeed = 42f
            showLocation(point, true, bearing)
            updateProgress(point, demoSpeed)
            status = "DEMO navegando"
            index = nextIndex
            mainHandler.postDelayed(runner, 700L)
        }
        demoRunnable = runner
        mainHandler.post(runner)
    }

    DisposableEffect(Unit) {
        onDispose {
            trackingListener?.let { try { locationManager.removeUpdates(it) } catch (_: Exception) { } }
            demoRunnable?.let { mainHandler.removeCallbacks(it) }
            tts.stop()
            tts.shutdown()
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { permissions ->
        val granted = permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true || permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true
        if (granted) requestLocation() else status = "Permiso de ubicación rechazado"
    }

    fun ensureLocationPermission() {
        val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (granted) requestLocation() else permissionLauncher.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION))
    }

    fun findDestination() {
        val query = searchText.trim()
        if (query.isEmpty()) {
            status = "Escribe un destino"
            return
        }
        status = "Buscando destino…"
        routeInfo = ""
        nextInstruction = ""
        nextDistance = ""
        remainingInfo = ""
        Thread {
            try {
                val result = searchPlace(query)
                mainHandler.post {
                    if (result != null) {
                        showDestination(result)
                        status = "Destino encontrado"
                    } else status = "No encontré ese destino"
                }
            } catch (_: Exception) {
                mainHandler.post { status = "Error buscando destino" }
            }
        }.start()
    }

    fun calculateRoute() {
        val dest = destination
        if (dest == null) {
            status = "Primero busca un destino"
            return
        }
        fun buildFrom(origin: LatLng) {
            status = "Calculando ruta…"
            Thread {
                try {
                    val route = fetchRoute(origin, dest.point)
                    mainHandler.post {
                        if (route != null) drawRoute(route, origin, dest.point) else status = "No pude calcular una ruta"
                    }
                } catch (_: Exception) {
                    mainHandler.post { status = "Error calculando ruta" }
                }
            }.start()
        }
        lastLocation?.let(::buildFrom) ?: requestLocation { point -> point?.let(::buildFrom) }
    }

    MaterialTheme(colorScheme = NetherisColors) {
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            Column(modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp, vertical = 8.dp)) {
                Text("NETHERIS GPS", fontSize = 23.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                Text("V1.5 · $status", color = Color(0xFF9EB8C8), fontSize = 13.sp)

                if (activeRoute != null) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Surface(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(14.dp), color = Color(0xFF102334)) {
                        Row(modifier = Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Column { Text("Restante", color = Color(0xFF8FAABA), fontSize = 11.sp); Text(remainingInfo.ifEmpty { "--" }, color = Color.White, fontWeight = FontWeight.Bold) }
                            Column { Text("Llegada", color = Color(0xFF8FAABA), fontSize = 11.sp); Text(etaInfo, color = Color.White, fontWeight = FontWeight.Bold) }
                            Column { Text("Velocidad", color = Color(0xFF8FAABA), fontSize = 11.sp); Text(speedInfo, color = Color.White, fontWeight = FontWeight.Bold) }
                        }
                    }
                }

                if (nextInstruction.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Surface(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(14.dp), color = Color(0xFF173247)) {
                        Row(modifier = Modifier.fillMaxWidth().padding(10.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(nextInstruction, color = Color.White, fontSize = 17.sp, fontWeight = FontWeight.Bold, modifier = Modifier.fillMaxWidth(0.76f))
                            Text(nextDistance, color = MaterialTheme.colorScheme.primary, fontSize = 17.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }

                Spacer(modifier = Modifier.height(5.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    OutlinedTextField(
                        value = searchText,
                        onValueChange = { searchText = it },
                        modifier = Modifier.fillMaxWidth(0.70f),
                        singleLine = true,
                        label = { Text("Destino") },
                        placeholder = { Text("Ej: Costanera Center") }
                    )
                    Button(
                        onClick = { findDestination() },
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary, contentColor = Color(0xFF0A0717))
                    ) { Text("Buscar") }
                }

                Spacer(modifier = Modifier.height(5.dp))
                Box(modifier = Modifier.fillMaxWidth().height(if (activeRoute != null) 235.dp else 310.dp)) {
                    NetherisMap(
                        modifier = Modifier.fillMaxSize(),
                        onMapReady = { readyMap ->
                            map = readyMap
                            status = "Mapa listo"
                            if (prefs.contains(HOME_LAT) && prefs.contains(HOME_LON)) {
                                showHome(
                                    LatLng(
                                        prefs.getLong(HOME_LAT, 0L).let(Double::fromBits),
                                        prefs.getLong(HOME_LON, 0L).let(Double::fromBits)
                                    ), false
                                )
                            }
                        }
                    )
                }

                Spacer(modifier = Modifier.height(5.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Button(onClick = { ensureLocationPermission() }, shape = RoundedCornerShape(12.dp), colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary, contentColor = MaterialTheme.colorScheme.onPrimary)) { Text("📍 Ubicación") }
                    Button(onClick = { calculateRoute() }, shape = RoundedCornerShape(12.dp), colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF21C7A8), contentColor = Color(0xFF001A16))) { Text("🚗 Ruta") }
                    Button(onClick = { if (navigationActive && !demoActive) stopNavigation() else startNavigation() }, shape = RoundedCornerShape(12.dp), colors = ButtonDefaults.buttonColors(containerColor = if (navigationActive && !demoActive) Color(0xFF8D3A4A) else Color(0xFF305B8E), contentColor = Color.White)) { Text(if (navigationActive && !demoActive) "⏹ Parar" else "▶ Navegar") }
                }

                Spacer(modifier = Modifier.height(4.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Button(onClick = { if (demoActive) stopNavigation() else startDemo() }, shape = RoundedCornerShape(12.dp), colors = ButtonDefaults.buttonColors(containerColor = if (demoActive) Color(0xFF8D3A4A) else Color(0xFF6A4C93), contentColor = Color.White)) { Text(if (demoActive) "⏹ Demo" else "▶ DEMO") }
                    Button(onClick = { voiceEnabled = !voiceEnabled; if (!voiceEnabled) tts.stop() }, shape = RoundedCornerShape(12.dp), colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF24384A), contentColor = Color.White)) { Text(if (voiceEnabled) "🔊 Voz" else "🔇 Voz") }
                    Button(
                        onClick = {
                            stopNavigation()
                            routePolyline?.let { poly -> map?.removePolyline(poly) }
                            routePolyline = null
                            destinationMarker?.let { marker -> map?.removeMarker(marker) }
                            destinationMarker = null
                            destination = null
                            activeRoute = null
                            routeInfo = ""
                            nextInstruction = ""
                            nextDistance = ""
                            remainingInfo = ""
                            speedInfo = "0 km/h"
                            etaInfo = "--:--"
                            status = "Ruta limpiada"
                        },
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF24384A), contentColor = Color.White)
                    ) { Text("Limpiar") }
                }
            }
        }
    }
}

@Composable
private fun NetherisMap(modifier: Modifier = Modifier, onMapReady: (MapLibreMap) -> Unit) {
    val context = LocalContext.current
    val mapView = remember { MapView(context) }
    AndroidView(
        modifier = modifier,
        factory = {
            mapView.apply {
                onCreate(null)
                onStart()
                onResume()
                getMapAsync { readyMap ->
                    readyMap.setStyle(MAP_STYLE) {
                        readyMap.cameraPosition = CameraPosition.Builder().target(Santiago).zoom(12.5).build()
                        onMapReady(readyMap)
                    }
                }
            }
        }
    )
    DisposableEffect(mapView) {
        onDispose {
            mapView.onPause()
            mapView.onStop()
            mapView.onDestroy()
        }
    }
}
