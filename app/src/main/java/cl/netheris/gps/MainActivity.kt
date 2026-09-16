package cl.netheris.gps

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.CancellationSignal
import android.os.Handler
import android.os.Looper
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
import java.util.Locale

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
private val Santiago = LatLng(-33.4489, -70.6693)

private data class SearchResult(val point: LatLng, val label: String)
private data class RouteResult(
    val points: List<LatLng>,
    val distanceMeters: Double,
    val durationSeconds: Double
)

private fun httpGet(url: String): String {
    val connection = URL(url).openConnection() as HttpURLConnection
    return try {
        connection.requestMethod = "GET"
        connection.connectTimeout = 10000
        connection.readTimeout = 15000
        connection.setRequestProperty("User-Agent", "NetherisGPS/1.2 Android")
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
        point = LatLng(item.getString("lat").toDouble(), item.getString("lon").toDouble()),
        label = item.optString("display_name", query)
    )
}

private fun fetchRoute(origin: LatLng, destination: LatLng): RouteResult? {
    val url = "https://router.project-osrm.org/route/v1/driving/" +
        "${origin.longitude},${origin.latitude};${destination.longitude},${destination.latitude}" +
        "?overview=full&geometries=geojson&steps=false"

    val root = JSONObject(httpGet(url))
    if (root.optString("code") != "Ok") return null
    val routes = root.optJSONArray("routes") ?: return null
    if (routes.length() == 0) return null

    val route = routes.getJSONObject(0)
    val coordinates = route
        .getJSONObject("geometry")
        .getJSONArray("coordinates")

    val points = ArrayList<LatLng>(coordinates.length())
    for (i in 0 until coordinates.length()) {
        val pair = coordinates.getJSONArray(i)
        points.add(LatLng(pair.getDouble(1), pair.getDouble(0)))
    }

    return RouteResult(
        points = points,
        distanceMeters = route.getDouble("distance"),
        durationSeconds = route.getDouble("duration")
    )
}

@Composable
fun NetherisGpsApp() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE) }
    val mainHandler = remember { Handler(Looper.getMainLooper()) }

    var map by remember { mutableStateOf<MapLibreMap?>(null) }
    var status by remember { mutableStateOf("Cargando mapa…") }
    var searchText by remember { mutableStateOf("") }
    var routeInfo by remember { mutableStateOf("") }
    var lastLocation by remember { mutableStateOf<LatLng?>(null) }
    var destination by remember { mutableStateOf<SearchResult?>(null) }
    var locationMarker by remember { mutableStateOf<Marker?>(null) }
    var homeMarker by remember { mutableStateOf<Marker?>(null) }
    var destinationMarker by remember { mutableStateOf<Marker?>(null) }
    var routePolyline by remember { mutableStateOf<Polyline?>(null) }

    fun showLocation(latLng: LatLng, moveCamera: Boolean = true) {
        val readyMap = map ?: return
        locationMarker?.let { readyMap.removeMarker(it) }
        locationMarker = readyMap.addMarker(
            MarkerOptions().position(latLng).title("Mi ubicación")
        )
        if (moveCamera) {
            readyMap.cameraPosition = CameraPosition.Builder()
                .target(latLng)
                .zoom(16.5)
                .build()
        }
        lastLocation = latLng
        status = "Ubicación encontrada"
    }

    fun showHome(latLng: LatLng, moveCamera: Boolean = true) {
        val readyMap = map ?: return
        homeMarker?.let { readyMap.removeMarker(it) }
        homeMarker = readyMap.addMarker(
            MarkerOptions().position(latLng).title("Casa · Netheris")
        )
        if (moveCamera) {
            readyMap.cameraPosition = CameraPosition.Builder()
                .target(latLng)
                .zoom(16.5)
                .build()
        }
    }

    fun showDestination(result: SearchResult) {
        val readyMap = map ?: return
        destinationMarker?.let { readyMap.removeMarker(it) }
        destinationMarker = readyMap.addMarker(
            MarkerOptions().position(result.point).title("Destino")
        )
        destination = result
        readyMap.cameraPosition = CameraPosition.Builder()
            .target(result.point)
            .zoom(16.0)
            .build()
    }

    fun drawRoute(result: RouteResult, origin: LatLng, dest: LatLng) {
        val readyMap = map ?: return
        routePolyline?.let { readyMap.removePolyline(it) }
        routePolyline = readyMap.addPolyline(
            PolylineOptions()
                .addAll(result.points)
                .color(0xFF30D5FF.toInt())
                .width(6f)
        )

        val boundsBuilder = LatLngBounds.Builder()
        boundsBuilder.include(origin)
        boundsBuilder.include(dest)
        result.points.forEach { boundsBuilder.include(it) }
        readyMap.animateCamera(
            CameraUpdateFactory.newLatLngBounds(boundsBuilder.build(), 80),
            800
        )

        val km = result.distanceMeters / 1000.0
        val minutes = result.durationSeconds / 60.0
        routeInfo = String.format(Locale.getDefault(), "%.1f km · %.0f min", km, minutes)
        status = "Ruta calculada"
    }

    fun requestLocation(onResult: (LatLng?) -> Unit = {}) {
        val locationManager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
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
                locationManager.getCurrentLocation(
                    provider,
                    CancellationSignal(),
                    ContextCompat.getMainExecutor(context),
                    handleLocation
                )
            } else {
                val gps = locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
                val network = locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
                handleLocation(gps ?: network)
            }
        } catch (_: SecurityException) {
            status = "No tengo permiso para acceder al GPS"
            onResult(null)
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val granted = permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
            permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true
        if (granted) requestLocation() else status = "Permiso de ubicación rechazado"
    }

    fun ensureLocationPermission() {
        val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (granted) {
            requestLocation()
        } else {
            permissionLauncher.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION))
        }
    }

    fun findDestination() {
        val query = searchText.trim()
        if (query.isEmpty()) {
            status = "Escribe un destino"
            return
        }
        status = "Buscando destino…"
        routeInfo = ""
        Thread {
            try {
                val result = searchPlace(query)
                mainHandler.post {
                    if (result != null) {
                        showDestination(result)
                        status = "Destino encontrado"
                    } else {
                        status = "No encontré ese destino"
                    }
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
                        if (route != null) {
                            drawRoute(route, origin, dest.point)
                        } else {
                            status = "No pude calcular una ruta"
                        }
                    }
                } catch (_: Exception) {
                    mainHandler.post { status = "Error calculando ruta" }
                }
            }.start()
        }

        val known = lastLocation
        if (known != null) {
            buildFrom(known)
        } else {
            requestLocation { point -> point?.let(::buildFrom) }
        }
    }

    MaterialTheme(colorScheme = NetherisColors) {
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 12.dp, vertical = 8.dp)
            ) {
                Text(
                    text = "NETHERIS GPS",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = "V1.2 · $status${if (routeInfo.isNotEmpty()) " · $routeInfo" else ""}",
                    color = Color(0xFF9EB8C8),
                    fontSize = 13.sp
                )

                Spacer(modifier = Modifier.height(6.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
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
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.secondary,
                            contentColor = Color(0xFF0A0717)
                        )
                    ) {
                        Text("Buscar")
                    }
                }

                Spacer(modifier = Modifier.height(6.dp))

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(360.dp)
                ) {
                    NetherisMap(
                        modifier = Modifier.fillMaxSize(),
                        onMapReady = { readyMap ->
                            map = readyMap
                            status = "Mapa listo"
                            if (prefs.contains(HOME_LAT) && prefs.contains(HOME_LON)) {
                                val home = LatLng(
                                    prefs.getLong(HOME_LAT, 0L).let(Double::fromBits),
                                    prefs.getLong(HOME_LON, 0L).let(Double::fromBits)
                                )
                                showHome(home, moveCamera = false)
                            }
                        }
                    )
                }

                Spacer(modifier = Modifier.height(6.dp))

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Button(
                        onClick = { ensureLocationPermission() },
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary,
                            contentColor = MaterialTheme.colorScheme.onPrimary
                        )
                    ) { Text("📍 Ubicación") }

                    Button(
                        onClick = { calculateRoute() },
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF21C7A8),
                            contentColor = Color(0xFF001A16)
                        )
                    ) { Text("🚗 Ruta") }

                    Button(
                        onClick = {
                            val save: (LatLng) -> Unit = { point ->
                                prefs.edit()
                                    .putLong(HOME_LAT, point.latitude.toBits())
                                    .putLong(HOME_LON, point.longitude.toBits())
                                    .apply()
                                showHome(point)
                                status = "Casa guardada"
                            }
                            lastLocation?.let(save) ?: requestLocation { point -> point?.let(save) }
                        },
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF24384A),
                            contentColor = Color.White
                        )
                    ) { Text("🏠 Guardar") }
                }

                Spacer(modifier = Modifier.height(4.dp))

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Button(
                        onClick = {
                            if (prefs.contains(HOME_LAT) && prefs.contains(HOME_LON)) {
                                val home = LatLng(
                                    prefs.getLong(HOME_LAT, 0L).let(Double::fromBits),
                                    prefs.getLong(HOME_LON, 0L).let(Double::fromBits)
                                )
                                showHome(home)
                                status = "Casa"
                            } else {
                                status = "Primero guarda Casa"
                            }
                        },
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.secondary,
                            contentColor = Color(0xFF0A0717)
                        )
                    ) { Text("🏡 Casa") }

                    Button(
                        onClick = {
                            routePolyline?.let { poly -> map?.removePolyline(poly) }
                            routePolyline = null
                            destinationMarker?.let { marker -> map?.removeMarker(marker) }
                            destinationMarker = null
                            destination = null
                            routeInfo = ""
                            status = "Ruta limpiada"
                        },
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF24384A),
                            contentColor = Color.White
                        )
                    ) { Text("Limpiar ruta") }

                    Button(
                        onClick = {
                            map?.cameraPosition = CameraPosition.Builder()
                                .target(Santiago)
                                .zoom(12.5)
                                .build()
                            status = "Vista Santiago"
                        },
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF24384A),
                            contentColor = Color.White
                        )
                    ) { Text("Santiago") }
                }
            }
        }
    }
}

@Composable
private fun NetherisMap(
    modifier: Modifier = Modifier,
    onMapReady: (MapLibreMap) -> Unit
) {
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
                        readyMap.cameraPosition = CameraPosition.Builder()
                            .target(Santiago)
                            .zoom(12.5)
                            .build()
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
