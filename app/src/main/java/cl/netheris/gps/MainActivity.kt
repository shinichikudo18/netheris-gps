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
import androidx.compose.foundation.layout.weight
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import org.maplibre.android.MapLibre
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

private const val MAP_STYLE = "https://demotiles.maplibre.org/style.json"
private val Santiago = LatLng(-33.4489, -70.6693)

@Composable
fun NetherisGpsApp() {
    val context = LocalContext.current
    var map by remember { mutableStateOf<MapLibreMap?>(null) }
    var status by remember { mutableStateOf("Mapa listo para navegar") }

    fun centerOnLocation() {
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
            return
        }

        val moveCamera: (Location?) -> Unit = { location ->
            if (location != null) {
                map?.cameraPosition = CameraPosition.Builder()
                    .target(LatLng(location.latitude, location.longitude))
                    .zoom(16.0)
                    .build()
                status = "Ubicación encontrada"
            } else {
                status = "No pude obtener una ubicación todavía"
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
                    return
                }

                status = "Buscando ubicación…"
                locationManager.getCurrentLocation(
                    provider,
                    CancellationSignal(),
                    ContextCompat.getMainExecutor(context),
                    moveCamera
                )
            } else {
                val gps = locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
                val network = locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
                moveCamera(gps ?: network)
            }
        } catch (_: SecurityException) {
            status = "No tengo permiso para acceder al GPS"
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val granted = permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
            permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true
        if (granted) centerOnLocation() else status = "Permiso de ubicación rechazado"
    }

    MaterialTheme(colorScheme = NetherisColors) {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = MaterialTheme.colorScheme.background
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(12.dp)
            ) {
                Text(
                    text = "NETHERIS GPS",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = "V1 · Santiago · $status",
                    color = Color(0xFF9EB8C8),
                    fontSize = 13.sp
                )

                Spacer(modifier = Modifier.height(10.dp))

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f)
                ) {
                    NetherisMap(
                        modifier = Modifier.fillMaxSize(),
                        onMapReady = { readyMap -> map = readyMap }
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Button(
                        onClick = {
                            val hasPermission = ContextCompat.checkSelfPermission(
                                context,
                                Manifest.permission.ACCESS_FINE_LOCATION
                            ) == PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(
                                context,
                                Manifest.permission.ACCESS_COARSE_LOCATION
                            ) == PackageManager.PERMISSION_GRANTED

                            if (hasPermission) {
                                centerOnLocation()
                            } else {
                                permissionLauncher.launch(
                                    arrayOf(
                                        Manifest.permission.ACCESS_FINE_LOCATION,
                                        Manifest.permission.ACCESS_COARSE_LOCATION
                                    )
                                )
                            }
                        },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary,
                            contentColor = MaterialTheme.colorScheme.onPrimary
                        )
                    ) {
                        Text("Mi ubicación")
                    }

                    Button(
                        onClick = {
                            map?.cameraPosition = CameraPosition.Builder()
                                .target(Santiago)
                                .zoom(11.5)
                                .build()
                            status = "Vista Santiago"
                        },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.secondary,
                            contentColor = Color(0xFF0A0717)
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
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val context = LocalContext.current
    val mapView = remember { MapView(context) }

    AndroidView(
        modifier = modifier,
        factory = {
            mapView.apply {
                onCreate(null)
                getMapAsync { readyMap ->
                    readyMap.setStyle(MAP_STYLE)
                    readyMap.cameraPosition = CameraPosition.Builder()
                        .target(Santiago)
                        .zoom(11.5)
                        .build()
                    onMapReady(readyMap)
                }
            }
        }
    )

    DisposableEffect(lifecycle, mapView) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_START -> mapView.onStart()
                Lifecycle.Event.ON_RESUME -> mapView.onResume()
                Lifecycle.Event.ON_PAUSE -> mapView.onPause()
                Lifecycle.Event.ON_STOP -> mapView.onStop()
                Lifecycle.Event.ON_DESTROY -> mapView.onDestroy()
                else -> Unit
            }
        }
        lifecycle.addObserver(observer)
        onDispose {
            lifecycle.removeObserver(observer)
            mapView.onDestroy()
        }
    }
}
