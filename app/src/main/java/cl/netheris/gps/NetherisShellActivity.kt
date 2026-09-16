package cl.netheris.gps

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
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
import androidx.compose.ui.graphics.Brush
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

private val NetherisDeep = Color(0xFF050B14)
private val NetherisPanel = Color(0xEE0A1724)
private val NetherisCyan = Color(0xFF5FE7FF)
private val NetherisViolet = Color(0xFF9D7CFF)
private val NetherisSoft = Color(0xFF9DB4C7)

class NetherisShellActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        MapLibre.getInstance(this)
        setContent {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        Brush.verticalGradient(
                            listOf(Color(0xFF08111C), NetherisDeep, Color(0xFF03070D))
                        )
                    )
                    .statusBarsPadding()
                    .navigationBarsPadding()
            ) {
                Column(modifier = Modifier.fillMaxSize()) {
                    NetherisHeader()
                    NavigationSessionCard()
                    Box(modifier = Modifier.fillMaxWidth().weight(1f)) {
                        NetherisGpsApp()
                    }
                }
            }
        }
    }
}

@Composable
private fun NetherisHeader() {
    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("◇", color = NetherisCyan, fontSize = 24.sp, fontWeight = FontWeight.Black)
                Column(modifier = Modifier.padding(start = 8.dp)) {
                    Text("NETHERIS", color = Color.White, fontSize = 17.sp, fontWeight = FontWeight.Black)
                    Text("NAVIGATION CORE · V5.0", color = NetherisSoft, fontSize = 9.sp, letterSpacing = 1.sp)
                }
            }
            Surface(
                shape = RoundedCornerShape(20.dp),
                color = Color(0x331DA7C5),
                modifier = Modifier.border(1.dp, Color(0x555FE7FF), RoundedCornerShape(20.dp))
            ) {
                Text("ONLINE", color = NetherisCyan, fontSize = 9.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp))
            }
        }
        Spacer(Modifier.height(5.dp))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(Brush.horizontalGradient(listOf(Color.Transparent, NetherisCyan, NetherisViolet, Color.Transparent)))
        )
    }
}

private data class RecentDestination(val label: String, val lat: Double, val lon: Double)

private fun latestRecent(context: Context): RecentDestination? {
    val prefs = context.getSharedPreferences("netheris_gps", Context.MODE_PRIVATE)
    return runCatching {
        val array = JSONArray(prefs.getString("recents_json", "[]") ?: "[]")
        if (array.length() == 0) return@runCatching null
        val o = array.getJSONObject(0)
        RecentDestination(o.optString("label", "Destino"), o.getDouble("lat"), o.getDouble("lon"))
    }.getOrNull()
}

@Composable
private fun NavigationSessionCard() {
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

    fun resumeBackground() {
        ContextCompat.startForegroundService(
            context,
            Intent(context, NavigationForegroundService::class.java).setAction(NavigationForegroundService.ACTION_RESUME)
        )
    }

    fun stopBackground() {
        context.startService(Intent(context, NavigationForegroundService::class.java).setAction(NavigationForegroundService.ACTION_STOP))
    }

    when {
        snapshot.active -> {
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 10.dp, vertical = 4.dp)
                    .border(1.dp, Color(0x6648DFF5), RoundedCornerShape(18.dp)),
                shape = RoundedCornerShape(18.dp),
                color = NetherisPanel,
                shadowElevation = 5.dp
            ) {
                Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 9.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text("◇ SESIÓN DE NAVEGACIÓN", color = NetherisCyan, fontSize = 10.sp, fontWeight = FontWeight.Black, letterSpacing = 0.8.sp)
                            Text(
                                snapshot.instruction.ifBlank { snapshot.destination.ifBlank { "Recuperando sesión…" } },
                                color = Color.White,
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                        Button(
                            onClick = { stopBackground() },
                            shape = RoundedCornerShape(14.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF321D2A), contentColor = Color(0xFFFFB7D0))
                        ) { Text("DETENER", fontSize = 9.sp, fontWeight = FontWeight.Bold) }
                    }
                    val stats = listOf(snapshot.nextDistance, snapshot.remaining, snapshot.eta, snapshot.speed).filter { it.isNotBlank() }
                    if (stats.isNotEmpty()) {
                        Spacer(Modifier.height(5.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            stats.forEachIndexed { index, value ->
                                Text(
                                    value,
                                    color = if (index == 0) NetherisCyan else Color(0xFFB9CDE0),
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }
                    }
                }
            }
        }
        snapshot.destinationLat != null && snapshot.destinationLon != null && snapshot.destination.isNotBlank() -> {
            Surface(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 3.dp),
                shape = RoundedCornerShape(16.dp),
                color = Color(0xCC091520)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("ÚLTIMA SESIÓN", color = NetherisSoft, fontSize = 9.sp, letterSpacing = 0.8.sp)
                        Text(snapshot.destination.substringBefore(","), color = Color.White, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    }
                    Button(
                        onClick = { resumeBackground() },
                        shape = RoundedCornerShape(13.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF123B4C), contentColor = NetherisCyan)
                    ) { Text("REANUDAR", fontSize = 9.sp, fontWeight = FontWeight.Bold) }
                }
            }
        }
        recent != null -> {
            Surface(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 3.dp),
                shape = RoundedCornerShape(16.dp),
                color = Color(0xB3091520)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        "◇ ${recent?.label?.substringBefore(",")?.take(32)}",
                        color = NetherisSoft,
                        fontSize = 11.sp,
                        modifier = Modifier.weight(1f),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Button(
                        onClick = { startBackground() },
                        shape = RoundedCornerShape(13.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF162A3B), contentColor = NetherisCyan)
                    ) { Text("INICIAR", fontSize = 9.sp, fontWeight = FontWeight.Bold) }
                }
            }
        }
    }
}
