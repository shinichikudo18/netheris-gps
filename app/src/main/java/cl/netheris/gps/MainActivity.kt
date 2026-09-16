package cl.netheris.gps

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.CancellationSignal
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
import org.maplibre.android.MapLibre
import org.maplibre.android.annotations.Marker
import org.maplibre.android.annotations.MarkerOptions
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapView

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

@Composable
fun NetherisGpsApp() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE) }

    var map by remember { mutableStateOf<MapLibreMap?>(null) }
    var status by remember { mutableStateOf("Cargando mapa…") }
    var lastLocation by remember { mutableStateOf<LatLng?>(null) }
    var locationMarker by remember { mutableStateOf<Marker?>(null) }
    var homeMarker by remember { mutableStateOf<Marker?>(null) }

    fun showLocation(latLng: LatLng) {
        val readyMap = map ?: return
        locationMarker?.let { readyMap.removeMarker(it) }
        locationMarker = readyMap.addMarker(
            MarkerOptions()
                .position(latLng)
                .title("Mi ubicación")
        )
        readyMap.cameraPosition = CameraPosition.Builder()
            .target(latLng)
            .zoom(16.5)
            .build()
        lastLocation = latLng
        status = "Ubicación encontrada"
    }

    fun showHome(latLng: LatLng, moveCamera: Boolean = true) {
        val readyMap = map ?: return
        homeMarker?.let { readyMap.removeMarker(it) }
        homeMarker = readyMap.addMarker(
            MarkerOptions()
                .position(latLng)
                .title("Casa · Netheris")
        )
        if (moveCamera) {
            readyMap.cameraPosition = CameraPosition.Builder()
                .target(latLng)
                .zoom(16.5)
                .build()
        }
    }

    fun requestLocation(onResult: (LatLng?) -> Unit = {}) {
        val locationManager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val hasFine = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        val hasCoarse = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        if (!hasFine && !hasCoarse) {
            status = "Necesito permiso de ubicación"
            onResult(null)
            return
        }

        val handleLocation: (Location?) -> Unit = { location ->
            if (location != null) {
                val latLng = LatLng(location.latitude, location.longitude)
                showLocation(latLng)
                onResult(latLng)
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
        val granted = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        if (granted) {
            requestLocation()
        } else {
            permissionLauncher.launch(
                arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION
                )
            )
        }
    }

    MaterialTheme(colorScheme = NetherisColors) {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = MaterialTheme.colorScheme.background
        ) {
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
                    text = "V1.1 · $status",
                    color = Color(0xFF9EB8C8),
                    fontSize = 13.sp
                )

                Spacer(modifier = Modifier.height(8.dp))

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(470.dp)
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

                Spacer(modifier = Modifier.height(8.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Button(
                        onClick = { ensureLocationPermission() },
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary,
                            contentColor = MaterialTheme.colorScheme.onPrimary
                        )
                    ) {
                        Text("📍 Mi ubicación")
                    }

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

                            val known = lastLocation
                            if (known != null) {
                                save(known)
                            } else {
                                requestLocation { point -> point?.let(save) }
                            }
                        },
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF24384A),
                            contentColor = Color.White
                        )
                    ) {
                        Text("🏠 Guardar casa")
                    }
                }

                Spacer(modifier = Modifier.height(6.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
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
                                status = "Primero guarda Casa desde tu ubicación"
                            }
                        },
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.secondary,
                            contentColor = Color(0xFF0A0717)
                        )
                    ) {
                        Text("🏡 Casa")
                    }

                    Button(
                        onClick = {
                            map?.cameraPosition = CameraPosition.Builder()
                                .target(Santiago)
                                .zoom(12.5)
                                .build()
                            status = "Vista Santiago"
                        },
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF24384A),
                            contentColor = Color.White
                        )
                    ) {
                        Text("Santiago")
                    }
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
