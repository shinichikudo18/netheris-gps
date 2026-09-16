package cl.netheris.gps

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
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
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .statusBarsPadding()
                    .navigationBarsPadding()
            ) {
                BackgroundNavigationBar()
                androidx.compose.foundation.layout.Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f)
                ) {
                    NetherisGpsApp()
                }
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
private fun BackgroundNavigationBar() {
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

    if (snapshot.active) {
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp, vertical = 4.dp),
            shape = RoundedCornerShape(14.dp),
            color = Color(0xFF0B2234),
            shadowElevation = 3.dp
        ) {
            Column(modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "◈ NETHERIS NAV · ACTIVA",
                            color = Color(0xFF6FE7FF),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = snapshot.instruction.ifBlank { snapshot.destination.ifBlank { "Esperando GPS…" } },
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                    Button(
                        onClick = { stopBackground() },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF503044),
                            contentColor = Color.White
                        )
                    ) { Text("⏹") }
                }

                val stats = listOf(snapshot.nextDistance, snapshot.remaining, snapshot.eta, snapshot.speed)
                    .filter { it.isNotBlank() }
                    .joinToString(" · ")
                if (stats.isNotBlank()) {
                    Spacer(Modifier.height(2.dp))
                    Text(stats, color = Color(0xFF9EDCF2), fontSize = 11.sp)
                }
            }
        }
    } else if (recent != null) {
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp, vertical = 3.dp),
            shape = RoundedCornerShape(12.dp),
            color = Color(0xFF0B1925)
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "◈ BG disponible · ${recent?.label?.substringBefore(",")?.take(26)}",
                    color = Color(0xFF9EB8C8),
                    fontSize = 11.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f)
                )
                Button(
                    onClick = { startBackground() },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color(0xFF173247),
                        contentColor = Color(0xFF6FE7FF)
                    )
                ) { Text("Iniciar", fontSize = 11.sp) }
            }
        }
    }
}
