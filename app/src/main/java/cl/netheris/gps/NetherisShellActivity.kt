package cl.netheris.gps

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
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
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import cl.netheris.gps.core.NavStateStore
import cl.netheris.gps.nav.NavigationForegroundService
import org.json.JSONArray
import org.maplibre.android.MapLibre

class NetherisShellActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        MapLibre.getInstance(this)
        setContent {
            Box(modifier = Modifier.fillMaxSize()) {
                NetherisGpsApp()
                BackgroundNavigationBridge()
            }
        }
    }
}

private data class RecentDestination(val label: String, val lat: Double, val lon: Double)

private fun latestRecent(context: Context): RecentDestination? {
    val prefs = context.getSharedPreferences("netheris_gps", Context.MODE_PRIVATE)
    return runCatching {
        val array = JSONArray(prefs.getString("recents_json", "[]") ?: "[]")
        if (array.length() == 0) return@runCatching null
        val o = array.getJSONObject(0)
        RecentDestination(
            o.optString("label", "Destino"),
            o.getDouble("lat"),
            o.getDouble("lon")
        )
    }.getOrNull()
}

@Composable
private fun BackgroundNavigationBridge() {
    val context = androidx.compose.ui.platform.LocalContext.current
    val handler = remember { Handler(Looper.getMainLooper()) }
    var snapshot by remember { mutableStateOf(NavStateStore.snapshot(context)) }
    var recent by remember { mutableStateOf(latestRecent(context)) }

    DisposableEffect(Unit) {
        lateinit var poll: Runnable
        poll = Runnable {
            snapshot = NavStateStore.snapshot(context)
            recent = latestRecent(context)
            handler.postDelayed(poll, 1000L)
        }
        handler.post(poll)
        onDispose { handler.removeCallbacks(poll) }
    }

    fun startBackground() {
        val r = recent ?: return
        val intent = Intent(context, NavigationForegroundService::class.java)
            .setAction(NavigationForegroundService.ACTION_START)
            .putExtra(NavigationForegroundService.EXTRA_LABEL, r.label)
            .putExtra(NavigationForegroundService.EXTRA_LAT, r.lat)
            .putExtra(NavigationForegroundService.EXTRA_LON, r.lon)
        ContextCompat.startForegroundService(context, intent)
    }

    fun stopBackground() {
        context.startService(
            Intent(context, NavigationForegroundService::class.java)
                .setAction(NavigationForegroundService.ACTION_STOP)
        )
    }

    Box(modifier = Modifier.fillMaxSize()) {
        if (snapshot.active) {
            Surface(
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .fillMaxWidth()
                    .padding(horizontal = 8.dp, vertical = 4.dp),
                shape = RoundedCornerShape(14.dp),
                color = Color(0xEE071B2B),
                shadowElevation = 8.dp
            ) {
                Column(modifier = Modifier.padding(10.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "◈ NETHERIS NAV · BG",
                                color = Color(0xFF6FE7FF),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = snapshot.destination.ifBlank { "Destino" },
                                color = Color.White,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                fontSize = 13.sp
                            )
                        }
                        Button(
                            onClick = { stopBackground() },
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF5D2942), contentColor = Color.White)
                        ) { Text("⏹") }
                    }
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = snapshot.instruction.ifBlank { "Esperando posición GPS…" },
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 15.sp,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                    val stats = listOf(snapshot.nextDistance, snapshot.remaining, snapshot.eta, snapshot.speed)
                        .filter { it.isNotBlank() }
                        .joinToString("  ·  ")
                    if (stats.isNotBlank()) {
                        Text(stats, color = Color(0xFF9EDCF2), fontSize = 12.sp)
                    }
                }
            }
        } else if (recent != null) {
            Button(
                onClick = { startBackground() },
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF173247), contentColor = Color(0xFF6FE7FF)),
                shape = RoundedCornerShape(16.dp)
            ) {
                Text("◈ BG", fontWeight = FontWeight.Bold)
            }
        }
    }
}
