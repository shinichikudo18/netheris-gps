from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# Animation / visual polish imports.
if 'import android.animation.ValueAnimator\n' not in s:
    s = s.replace('import android.Manifest\n', 'import android.Manifest\nimport android.animation.ValueAnimator\n')
if 'import android.view.animation.DecelerateInterpolator\n' not in s:
    s = s.replace('import android.speech.tts.TextToSpeech\n', 'import android.speech.tts.TextToSpeech\nimport android.view.animation.DecelerateInterpolator\n')
if 'import androidx.compose.animation.core.RepeatMode\n' not in s:
    s = s.replace(
        'import androidx.activity.result.contract.ActivityResultContracts\n',
        'import androidx.activity.result.contract.ActivityResultContracts\nimport androidx.compose.animation.core.RepeatMode\nimport androidx.compose.animation.core.animateFloat\nimport androidx.compose.animation.core.infiniteRepeatable\nimport androidx.compose.animation.core.rememberInfiniteTransition\nimport androidx.compose.animation.core.tween\n'
    )
if 'import androidx.compose.material3.LinearProgressIndicator\n' not in s:
    s = s.replace('import androidx.compose.material3.MaterialTheme\n', 'import androidx.compose.material3.MaterialTheme\nimport androidx.compose.material3.LinearProgressIndicator\n')
if 'import androidx.compose.ui.graphics.graphicsLayer\n' not in s:
    s = s.replace('import androidx.compose.ui.graphics.Color\n', 'import androidx.compose.ui.graphics.Color\nimport androidx.compose.ui.graphics.graphicsLayer\n')
if 'import kotlin.math.ceil\n' not in s:
    s = s.replace('import kotlin.math.max\n', 'import kotlin.math.ceil\nimport kotlin.math.max\n')

# v12 state: smooth vehicle interpolation, route progress and modern trip bar.
state_anchor = '    var lastCameraUpdateAt by remember { mutableStateOf(0L) }\n'
if state_anchor not in s:
    raise SystemExit('v11 camera timing anchor not found')
s = s.replace(
    state_anchor,
    state_anchor +
    '    var vehicleAnimator by remember { mutableStateOf<ValueAnimator?>(null) }\n'
    '    var renderedVehiclePosition by remember { mutableStateOf<LatLng?>(null) }\n'
    '    var routeProgress by remember { mutableStateOf(0f) }\n'
    '    var remainingTimeInfo by remember { mutableStateOf("-- min") }\n'
    '    var lastManualMapInteractionAt by remember { mutableStateOf(0L) }\n'
)

# Animate one marker smoothly between GPS fixes instead of jumping directly.
old_marker_update = '''        } else {\n            marker.position = latLng\n            marker.title = if (demoActive) "Demo" else if (isNav) "Netheris Vehicle" else "Mi ubicación"\n            marker.icon = desiredIcon\n            readyMap.updateMarker(marker)\n        }\n'''
new_marker_update = '''        } else {\n            marker.title = if (demoActive) "Demo" else if (isNav) "Netheris Vehicle" else "Mi ubicación"\n            marker.icon = desiredIcon\n            if (isNav) {\n                vehicleAnimator?.cancel()\n                val start = renderedVehiclePosition ?: marker.position ?: latLng\n                val end = latLng\n                val animator = ValueAnimator.ofFloat(0f, 1f).apply {\n                    duration = if (demoActive) 620L else 1050L\n                    interpolator = DecelerateInterpolator()\n                    addUpdateListener { animation ->\n                        val f = animation.animatedValue as Float\n                        val p = LatLng(\n                            start.latitude + (end.latitude - start.latitude) * f,\n                            start.longitude + (end.longitude - start.longitude) * f\n                        )\n                        marker.position = p\n                        renderedVehiclePosition = p\n                        runCatching { readyMap.updateMarker(marker) }\n                    }\n                }\n                vehicleAnimator = animator\n                animator.start()\n            } else {\n                marker.position = latLng\n                renderedVehiclePosition = latLng\n                readyMap.updateMarker(marker)\n            }\n        }\n'''
if old_marker_update not in s:
    raise SystemExit('v11 marker update anchor not found')
s = s.replace(old_marker_update, new_marker_update, 1)

# Initialize the rendered position when the marker is first created.
first_marker_anchor = '''            locationMarker = readyMap.addMarker(\n                MarkerOptions()\n                    .position(latLng)\n                    .title(if (demoActive) "Demo" else if (isNav) "Netheris Vehicle" else "Mi ubicación")\n                    .icon(desiredIcon)\n            )\n'''
if first_marker_anchor not in s:
    raise SystemExit('first location marker anchor not found')
s = s.replace(first_marker_anchor, first_marker_anchor + '            renderedVehiclePosition = latLng\n', 1)

# Let the camera glide across most of the GPS interval rather than snap in 240ms.
s = s.replace(
    'readyMap.animateCamera(CameraUpdateFactory.newCameraPosition(builder.build()), 240)',
    'readyMap.animateCamera(CameraUpdateFactory.newCameraPosition(builder.build()), if (isNav) 850 else 300)',
    1
)

# Update route progress and time remaining for a modern navigation trip bar.
progress_anchor = '''        val secondsRemaining = route.durationSeconds * fraction\n        etaInfo = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(System.currentTimeMillis() + (secondsRemaining * 1000).toLong()))\n        remainingInfo = formatDistance(remainingMeters)\n'''
if progress_anchor not in s:
    raise SystemExit('progress calculation anchor not found')
s = s.replace(
    progress_anchor,
    '''        val secondsRemaining = route.durationSeconds * fraction\n        routeProgress = (1.0 - fraction).toFloat().coerceIn(0f, 1f)\n        remainingTimeInfo = "${ceil(secondsRemaining / 60.0).toInt().coerceAtLeast(1)} min"\n        etaInfo = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(System.currentTimeMillis() + (secondsRemaining * 1000).toLong()))\n        remainingInfo = formatDistance(remainingMeters)\n''',
    1
)

# Route overview helper: like modern navigation apps, show the complete route and let CENTRAR resume follow.
calc_anchor = '''    fun cycleAlternative() {\n'''
if calc_anchor not in s:
    raise SystemExit('cycleAlternative anchor not found')
overview_helper = r'''    fun showRouteOverview() {
        val route = activeRoute ?: run { status = "Sin ruta activa"; return }
        val readyMap = map ?: return
        if (route.points.isEmpty()) return
        cameraFollowEnabled = false
        val boundsBuilder = LatLngBounds.Builder()
        route.points.forEach { boundsBuilder.include(it) }
        destination?.let { boundsBuilder.include(it.point) }
        lastLocation?.let { boundsBuilder.include(it) }
        runCatching {
            readyMap.animateCamera(CameraUpdateFactory.newLatLngBounds(boundsBuilder.build(), 70), 650)
        }
        status = "Resumen de ruta · toca CENTRAR para seguir"
    }

'''
s = s.replace(calc_anchor, overview_helper + calc_anchor, 1)

# Auto recenter after the user has left the map free for a few seconds.
manual_anchor = '''                                    if ((navigationActive || demoActive) && reason == MapLibreMap.OnCameraMoveStartedListener.REASON_API_GESTURE) {\n                                        cameraFollowEnabled = false\n                                        status = "Mapa libre · toca CENTRAR para seguir a Katherine"\n                                    }\n'''
if manual_anchor not in s:
    raise SystemExit('manual camera gesture anchor not found')
s = s.replace(
    manual_anchor,
    '''                                    if ((navigationActive || demoActive) && reason == MapLibreMap.OnCameraMoveStartedListener.REASON_API_GESTURE) {\n                                        cameraFollowEnabled = false\n                                        lastManualMapInteractionAt = SystemClock.elapsedRealtime()\n                                        status = "Mapa libre · Katherine volverá al seguimiento"\n                                        mainHandler.postDelayed({\n                                            val idleFor = SystemClock.elapsedRealtime() - lastManualMapInteractionAt\n                                            if ((navigationActive || demoActive) && !cameraFollowEnabled && idleFor >= 7500L) {\n                                                cameraFollowEnabled = true\n                                                val p = lastLocation\n                                                if (p != null) {\n                                                    val routeBearing = activeRoute?.let { route ->\n                                                        if (route.points.size < 2) null else {\n                                                            val idx = nearestRouteIndex(p, route.points)\n                                                            val ahead = (idx + 5).coerceAtMost(route.points.lastIndex)\n                                                            if (ahead > idx) bearingBetween(route.points[idx], route.points[ahead]) else null\n                                                        }\n                                                    }\n                                                    showLocation(p, true, routeBearing, lastSpeedKmh)\n                                                }\n                                                status = "Seguimiento automático restaurado"\n                                            }\n                                        }, 7600L)\n                                    }\n''',
    1
)

# Pulse detail for Katherine's NAV state; subtle Netheris HUD animation.
tools_anchor = '    var toolsExpanded by remember { mutableStateOf(false) }\n'
if tools_anchor not in s:
    raise SystemExit('tools state anchor not found')
s = s.replace(
    tools_anchor,
    tools_anchor +
    '    val hudPulseTransition = rememberInfiniteTransition(label = "netherisHud")\n'
    '    val hudPulse by hudPulseTransition.animateFloat(\n'
    '        initialValue = 0.45f, targetValue = 1f,\n'
    '        animationSpec = infiniteRepeatable(tween(900), RepeatMode.Reverse),\n'
    '        label = "hudPulse"\n'
    '    )\n'
)

# Maneuver glyph so the main guidance card is faster to read.
immersive_decl = '    val immersiveMode = navigationActive || demoActive || coreActive\n'
if immersive_decl not in s:
    raise SystemExit('immersive mode declaration not found')
s = s.replace(
    immersive_decl,
    immersive_decl +
    '    val maneuverGlyph = when {\n'
    '        nextInstruction.contains("izquierda", true) -> "↰"\n'
    '        nextInstruction.contains("derecha", true) -> "↱"\n'
    '        nextInstruction.contains("retorno", true) -> "↶"\n'
    '        nextInstruction.contains("rotonda", true) -> "⟳"\n'
    '        else -> "↑"\n'
    '    }\n'
)

# Add the glyph to guidance text.
s = s.replace(
    'nextInstruction.ifBlank { if (immersiveMode) "Katherine está siguiendo la ruta" else "Ruta preparada" },',
    '(if (immersiveMode) "$maneuverGlyph  " else "") + nextInstruction.ifBlank { if (immersiveMode) "Katherine está siguiendo la ruta" else "Ruta preparada" },',
    1
)

# Add progress bar after the trip statistics in the maneuver card.
trip_stats = '''                                Text(\n                                    "$remainingInfo restante   ·   ETA $etaInfo   ·   $speedInfo",\n                                    color = Color(0xFFA6C0D2),\n                                    fontSize = 11.sp,\n                                    fontWeight = FontWeight.SemiBold\n                                )\n'''
if trip_stats not in s:
    raise SystemExit('maneuver trip stats anchor not found')
s = s.replace(
    trip_stats,
    trip_stats + '''                                if (immersiveMode) {\n                                    Spacer(Modifier.height(5.dp))\n                                    LinearProgressIndicator(\n                                        progress = { routeProgress },\n                                        modifier = Modifier.fillMaxWidth().height(3.dp),\n                                        color = Color(0xFF5FE7FF),\n                                        trackColor = Color(0xFF173041)\n                                    )\n                                }\n''',
    1
)

# Modern trip bar between map and dock during navigation.
dock_spacer = '''                Spacer(Modifier.height(7.dp))\n                Surface(\n                    modifier = Modifier\n                        .fillMaxWidth()\n                        .navigationBarsPadding(),\n'''
if dock_spacer not in s:
    raise SystemExit('dock surface anchor not found')
trip_bar = r'''                if (immersiveMode) {
                    Spacer(Modifier.height(5.dp))
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                        color = Color(0xF20A1823)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 7.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column {
                                Text(etaInfo, color = Color(0xFF69F7C8), fontSize = 15.sp, fontWeight = FontWeight.Black)
                                Text("LLEGADA", color = Color(0xFF70899A), fontSize = 7.sp, fontWeight = FontWeight.Bold)
                            }
                            Column {
                                Text(remainingTimeInfo, color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Black)
                                Text("TIEMPO", color = Color(0xFF70899A), fontSize = 7.sp, fontWeight = FontWeight.Bold)
                            }
                            Column {
                                Text(remainingInfo, color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Black)
                                Text("RESTANTE", color = Color(0xFF70899A), fontSize = 7.sp, fontWeight = FontWeight.Bold)
                            }
                            Text("●", color = Color(0xFF5FE7FF), fontSize = 16.sp, modifier = Modifier.graphicsLayer(alpha = hudPulse))
                        }
                    }
                }

'''
s = s.replace(dock_spacer, trip_bar + dock_spacer, 1)

# Add route overview to the bottom sheet's first action row.
alt_button = 'TextButton(onClick = { toolsExpanded = false; cycleAlternative() }) { Text("ALTERNATIVAS", color = Color(0xFF9BCFFF), fontSize = 9.sp) }\n'
if alt_button not in s:
    raise SystemExit('bottom sheet alternatives button not found')
s = s.replace(
    alt_button,
    alt_button + '                                TextButton(onClick = { toolsExpanded = false; showRouteOverview() }) { Text("RESUMEN", color = Color(0xFF69F7C8), fontSize = 9.sp) }\n',
    1
)

# Cancel animation cleanly when navigation/composition ends.
s = s.replace(
    '            demoRunnable?.let { mainHandler.removeCallbacks(it) }\n            tts.stop(); tts.shutdown()\n',
    '            demoRunnable?.let { mainHandler.removeCallbacks(it) }\n            vehicleAnimator?.cancel()\n            tts.stop(); tts.shutdown()\n',
    1
)

# v12 version strings.
s = s.replace('NetherisGPS/11.0 Android', 'NetherisGPS/12.0 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text().replace('NETHERIS NAVIGATION AI · V11.0', 'NETHERIS NAVIGATION AI · V12.0')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 110', 'versionCode = 120').replace('versionName = "11.0.0"', 'versionName = "12.0.0"')
build.write_text(b)

print('Applied Netheris GPS v12 smooth navigation + modern trip HUD')
