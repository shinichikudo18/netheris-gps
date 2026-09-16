from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# Nav core state import.
if 'import cl.netheris.gps.core.NavStateStore\n' not in s:
    s = s.replace(
        'import cl.netheris.gps.nav.NavigationForegroundService\n',
        'import cl.netheris.gps.nav.NavigationForegroundService\nimport cl.netheris.gps.core.NavStateStore\n'
    )

# Extra UI/core-sync state.
anchor = '    var arrivedDestination by remember { mutableStateOf<SearchResult?>(null) }\n'
if anchor not in s:
    raise SystemExit('v10 arrival state anchor not found')
s = s.replace(
    anchor,
    anchor +
    '    var coreActive by remember { mutableStateOf(NavStateStore.snapshot(context).active) }\n'
    '    var coreRestoreAttempted by remember { mutableStateOf(false) }\n'
    '    var searchPanelOpen by remember { mutableStateOf(false) }\n'
)

# Smart start/search resets collapsed search state.
s = s.replace(
    '        stopNavigation(); cameraFollowEnabled = true; arrivalVisible = false; navigationActive = true; status = "Navegando"; speak("Navegación iniciada")\n',
    '        stopNavigation(); cameraFollowEnabled = true; arrivalVisible = false; searchPanelOpen = false; navigationActive = true; coreActive = true; status = "Navegando"; speak("Navegación iniciada")\n'
)

# Full reset clears local core presentation too.
s = s.replace(
    '        cameraFollowEnabled = true\n        lastSpeedKmh = 0f\n',
    '        cameraFollowEnabled = true\n        lastSpeedKmh = 0f\n        coreActive = false\n        coreRestoreAttempted = false\n        searchPanelOpen = false\n'
)

# Use route direction as a bearing fallback while stationary/no GPS bearing.
old_live = '''            val speed = if (location.hasSpeed()) location.speed * 3.6f else 0f\n            showLocation(point, true, if (location.hasBearing()) location.bearing else null, speed)\n            updateProgress(point, speed)\n'''
new_live = '''            val speed = if (location.hasSpeed()) location.speed * 3.6f else 0f\n            val routeBearing = activeRoute?.let { currentRoute ->\n                if (currentRoute.points.size < 2) null else {\n                    val routeIndex = nearestRouteIndex(point, currentRoute.points)\n                    val aheadIndex = (routeIndex + 5).coerceAtMost(currentRoute.points.lastIndex)\n                    if (aheadIndex > routeIndex) bearingBetween(currentRoute.points[routeIndex], currentRoute.points[aheadIndex]) else null\n                }\n            }\n            val cameraBearing = if (location.hasBearing() && speed >= 5f) location.bearing else routeBearing\n            showLocation(point, true, cameraBearing, speed)\n            updateProgress(point, speed)\n'''
if old_live not in s:
    raise SystemExit('live nav camera anchor not found')
s = s.replace(old_live, new_live)

# Add a core-state poll/restore effect before the permission launcher.
perm_anchor = '    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { p ->\n'
if perm_anchor not in s:
    raise SystemExit('permission launcher anchor not found')
core_effect = r'''    DisposableEffect(context, map) {
        lateinit var corePoll: Runnable
        corePoll = Runnable {
            val snap = NavStateStore.snapshot(context)
            coreActive = snap.active
            if (
                snap.active &&
                !navigationActive &&
                !demoActive &&
                !coreRestoreAttempted &&
                map != null &&
                snap.destinationLat != null &&
                snap.destinationLon != null
            ) {
                coreRestoreAttempted = true
                searchPanelOpen = false
                selectDestination(
                    SearchResult(
                        LatLng(snap.destinationLat, snap.destinationLon),
                        snap.destination.ifBlank { "Destino" }
                    ),
                    false
                )
                status = "Sincronizando navegación con Nav Core…"
                startNavigation()
            }
            mainHandler.postDelayed(corePoll, 1000L)
        }
        mainHandler.post(corePoll)
        onDispose { mainHandler.removeCallbacks(corePoll) }
    }

'''
s = s.replace(perm_anchor, core_effect + perm_anchor)

# Core state participates in immersive/navigation UI.
s = s.replace(
    '    val immersiveMode = navigationActive || demoActive\n',
    '    val immersiveMode = navigationActive || demoActive || coreActive\n'
)

# Search is hidden while navigating unless explicitly reopened.
s = s.replace(
    '                if (!immersiveMode) {\n',
    '                if (!immersiveMode || searchPanelOpen) {\n'
)

# If search is opened during navigation, keep it compact and clear route only when a new result is actually selected.
# Add a compact indicator when navigating and search is hidden.
map_spacer_anchor = '                Spacer(Modifier.height(5.dp))\n                Surface(\n                    modifier = Modifier.fillMaxWidth(),\n                    shape = RoundedCornerShape(22.dp),\n'
if map_spacer_anchor not in s:
    raise SystemExit('map surface anchor not found')
compact = r'''                if (immersiveMode && !searchPanelOpen) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(top = 3.dp, bottom = 2.dp),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("KATHERINE · MAPA EN SEGUIMIENTO", color = Color(0xFF6BE7FF), fontSize = 9.sp, fontWeight = FontWeight.Black)
                        Text(if (cameraFollowEnabled) "AUTO" else "LIBRE", color = if (cameraFollowEnabled) Color(0xFF69F7C8) else Color(0xFFFFD783), fontSize = 9.sp, fontWeight = FontWeight.Black)
                    }
                }

'''
s = s.replace(map_spacer_anchor, compact + map_spacer_anchor)

# Replace immersive dock middle controls: DETENER / CENTRAR / BUSCAR / more.
old_immersive = '''                            immersiveMode -> {\n                                Button(\n                                    onClick = { resetToExploration() },\n                                    modifier = Modifier.weight(1f),\n                                    shape = RoundedCornerShape(17.dp),\n                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF54263B), contentColor = Color.White)\n                                ) { Text("DETENER", fontSize = 9.sp, fontWeight = FontWeight.Black) }\n                                Button(\n                                    onClick = { voiceEnabled = !voiceEnabled; if (!voiceEnabled) tts.stop() },\n                                    modifier = Modifier.weight(1f),\n                                    shape = RoundedCornerShape(17.dp),\n                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF173447), contentColor = Color(0xFF67E8FF))\n                                ) { Text(if (voiceEnabled) "VOZ" else "MUTE", fontSize = 9.sp, fontWeight = FontWeight.Black) }\n                                Button(\n                                    onClick = { cameraFollowEnabled = true; lastLocation?.let { showLocation(it, true, null, lastSpeedKmh) } ?: ensureLocation(); status = "Seguimiento de cámara activo" },\n                                    modifier = Modifier.weight(1f),\n                                    shape = RoundedCornerShape(17.dp),\n                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF173447), contentColor = Color.White)\n                                ) { Text("CENTRAR", fontSize = 9.sp, fontWeight = FontWeight.Black) }\n                            }\n'''
new_immersive = '''                            immersiveMode -> {\n                                Button(\n                                    onClick = { resetToExploration() },\n                                    modifier = Modifier.weight(1f),\n                                    shape = RoundedCornerShape(17.dp),\n                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF54263B), contentColor = Color.White)\n                                ) { Text("DETENER", fontSize = 8.sp, fontWeight = FontWeight.Black) }\n                                Button(\n                                    onClick = {\n                                        cameraFollowEnabled = true\n                                        val point = lastLocation\n                                        if (point != null) {\n                                            val routeBearing = activeRoute?.let { route ->\n                                                if (route.points.size < 2) null else {\n                                                    val idx = nearestRouteIndex(point, route.points)\n                                                    val ahead = (idx + 5).coerceAtMost(route.points.lastIndex)\n                                                    if (ahead > idx) bearingBetween(route.points[idx], route.points[ahead]) else null\n                                                }\n                                            }\n                                            showLocation(point, true, routeBearing, lastSpeedKmh)\n                                        } else ensureLocation()\n                                        status = "Seguimiento de cámara activo"\n                                    },\n                                    modifier = Modifier.weight(1f),\n                                    shape = RoundedCornerShape(17.dp),\n                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF173447), contentColor = Color(0xFF67E8FF))\n                                ) { Text("CENTRAR", fontSize = 8.sp, fontWeight = FontWeight.Black) }\n                                Button(\n                                    onClick = { searchPanelOpen = !searchPanelOpen },\n                                    modifier = Modifier.weight(1f),\n                                    shape = RoundedCornerShape(17.dp),\n                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF334E86), contentColor = Color.White)\n                                ) { Text(if (searchPanelOpen) "MAPA" else "BUSCAR", fontSize = 8.sp, fontWeight = FontWeight.Black) }\n                            }\n'''
if old_immersive not in s:
    raise SystemExit('v10 immersive dock anchor not found')
s = s.replace(old_immersive, new_immersive)

# Selecting a destination while an existing session is active explicitly ends the old session first.
select_anchor = '''    fun selectDestination(result: SearchResult, moveCamera: Boolean = true) {\n        val readyMap = map ?: return\n'''
if select_anchor not in s:
    raise SystemExit('selectDestination function anchor not found')
s = s.replace(
    select_anchor,
    '''    fun selectDestination(result: SearchResult, moveCamera: Boolean = true) {\n        val readyMap = map ?: return\n        if ((navigationActive || coreActive) && searchPanelOpen) {\n            stopNavigation()\n            runCatching {\n                context.startService(Intent(context, NavigationForegroundService::class.java).setAction(NavigationForegroundService.ACTION_STOP))\n            }\n            navigationActive = false\n            coreActive = false\n            coreRestoreAttempted = false\n        }\n        searchPanelOpen = false\n'''
)

# Version strings.
s = s.replace('NetherisGPS/10.0 Android', 'NetherisGPS/10.1 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text().replace('NETHERIS NAVIGATION AI · V10.0', 'NETHERIS NAVIGATION AI · V10.1')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 100', 'versionCode = 101').replace('versionName = "10.0.0"', 'versionName = "10.1.0"')
build.write_text(b)

print('Applied Netheris GPS v10.1 nav sync + compact search + route-bearing camera')
