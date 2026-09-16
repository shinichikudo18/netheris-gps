from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# Full-screen landscape navigation branch. Keep the approved portrait UI untouched.
anchor = '    MaterialTheme(colorScheme = NetherisColors) {\n'
if anchor not in s:
    raise SystemExit('MaterialTheme anchor not found')

landscape = r'''    if (isLandscape && immersiveMode) {
        MaterialTheme(colorScheme = NetherisColors) {
            Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                Box(modifier = Modifier.fillMaxSize()) {
                    NetherisMap(
                        modifier = Modifier.fillMaxSize(),
                        onMapReady = { readyMap ->
                            map = readyMap
                            status = if (navigationActive || coreActive) "Navegando" else "Mapa listo"
                            if (prefs.contains(HOME_LAT) && prefs.contains(HOME_LON)) {
                                showHome(
                                    LatLng(
                                        prefs.getLong(HOME_LAT, 0L).let(Double::fromBits),
                                        prefs.getLong(HOME_LON, 0L).let(Double::fromBits)
                                    ),
                                    false
                                )
                            }
                            lastLocation?.let { p ->
                                val routeBearing = activeRoute?.let { route ->
                                    if (route.points.size < 2) null else {
                                        val idx = nearestRouteIndex(p, route.points)
                                        val ahead = (idx + 5).coerceAtMost(route.points.lastIndex)
                                        if (ahead > idx) bearingBetween(route.points[idx], route.points[ahead]) else null
                                    }
                                }
                                showLocation(p, true, routeBearing, lastSpeedKmh)
                            }
                        },
                        onLongPress = { point ->
                            if (searchPanelOpen) selectDestination(SearchResult(point, "Punto en mapa"), false)
                        }
                    )

                    // Top-left floating maneuver HUD.
                    Surface(
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .padding(start = 12.dp, top = 10.dp)
                            .fillMaxWidth(0.62f),
                        shape = RoundedCornerShape(20.dp),
                        color = Color(0xE8091824),
                        shadowElevation = 10.dp
                    ) {
                        Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 11.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    "KATHERINE · GUIANDO",
                                    color = Color(0xFF64E8FF),
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Black
                                )
                                Text(
                                    if (cameraFollowEnabled) "AUTO" else "LIBRE",
                                    color = if (cameraFollowEnabled) Color(0xFF69F7C8) else Color(0xFFFFD783),
                                    fontSize = 9.sp,
                                    fontWeight = FontWeight.Black
                                )
                            }
                            Spacer(Modifier.height(5.dp))
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.Top
                            ) {
                                Text(
                                    "$maneuverGlyph  " + nextInstruction.ifBlank { "Katherine está siguiendo la ruta" },
                                    modifier = Modifier.fillMaxWidth(0.82f),
                                    color = Color.White,
                                    fontSize = 18.sp,
                                    fontWeight = FontWeight.Black,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis
                                )
                                Text(
                                    nextDistance,
                                    color = Color(0xFF5FE7FF),
                                    fontSize = 18.sp,
                                    fontWeight = FontWeight.Black
                                )
                            }
                            Spacer(Modifier.height(5.dp))
                            Text(
                                "$remainingInfo restante   ·   ETA $etaInfo   ·   $speedInfo",
                                color = Color(0xFFA6C0D2),
                                fontSize = 10.sp,
                                fontWeight = FontWeight.SemiBold
                            )
                            Spacer(Modifier.height(5.dp))
                            LinearProgressIndicator(
                                progress = { routeProgress },
                                modifier = Modifier.fillMaxWidth().height(3.dp),
                                color = Color(0xFF5FE7FF),
                                trackColor = Color(0xFF173041)
                            )
                        }
                    }

                    // Compact Katherine status in the opposite corner.
                    Surface(
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .padding(end = 12.dp, top = 10.dp),
                        shape = RoundedCornerShape(18.dp),
                        color = Color(0xDD091722),
                        shadowElevation = 8.dp
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            KatherineAvatar(size = 30.dp)
                            Column(modifier = Modifier.padding(start = 7.dp)) {
                                Text("KATHERINE", color = Color.White, fontSize = 10.sp, fontWeight = FontWeight.Black)
                                Text("NAV CORE · ONLINE", color = Color(0xFF69F7C8), fontSize = 7.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }

                    // Optional floating search panel; map remains visible behind it.
                    if (searchPanelOpen) {
                        Surface(
                            modifier = Modifier
                                .align(Alignment.CenterEnd)
                                .padding(end = 12.dp)
                                .fillMaxWidth(0.44f),
                            shape = RoundedCornerShape(20.dp),
                            color = Color(0xEE081722),
                            shadowElevation = 12.dp
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Text("NUEVO DESTINO", color = Color(0xFF66E7FF), fontSize = 9.sp, fontWeight = FontWeight.Black)
                                Spacer(Modifier.height(5.dp))
                                OutlinedTextField(
                                    value = searchText,
                                    onValueChange = { searchText = it },
                                    modifier = Modifier.fillMaxWidth(),
                                    singleLine = true,
                                    label = { Text("¿A dónde vamos?") }
                                )
                                Spacer(Modifier.height(5.dp))
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                    Button(
                                        onClick = { findDestination() },
                                        modifier = Modifier.weight(1f),
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2D5D91), contentColor = Color.White)
                                    ) { Text("BUSCAR", fontSize = 8.sp, fontWeight = FontWeight.Black) }
                                    Button(
                                        onClick = { searchPanelOpen = false },
                                        modifier = Modifier.weight(1f),
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF173447), contentColor = Color.White)
                                    ) { Text("CERRAR", fontSize = 8.sp, fontWeight = FontWeight.Black) }
                                }
                                searchResults.take(3).forEach { result ->
                                    TextButton(
                                        onClick = { selectDestination(result) },
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        Text(result.label, color = Color.White, fontSize = 9.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                    }
                                }
                            }
                        }
                    }

                    // Floating navigation dock. Never consumes map height.
                    Surface(
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .padding(horizontal = 14.dp, vertical = 10.dp)
                            .navigationBarsPadding(),
                        shape = RoundedCornerShape(22.dp),
                        color = Color(0xEE071520),
                        shadowElevation = 12.dp
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 7.dp, vertical = 6.dp),
                            horizontalArrangement = Arrangement.spacedBy(6.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Button(
                                onClick = { resetToExploration() },
                                shape = RoundedCornerShape(16.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF54263B), contentColor = Color.White)
                            ) { Text("DETENER", fontSize = 8.sp, fontWeight = FontWeight.Black) }
                            Button(
                                onClick = {
                                    cameraFollowEnabled = true
                                    val p = lastLocation
                                    if (p != null) {
                                        val routeBearing = activeRoute?.let { route ->
                                            if (route.points.size < 2) null else {
                                                val idx = nearestRouteIndex(p, route.points)
                                                val ahead = (idx + 5).coerceAtMost(route.points.lastIndex)
                                                if (ahead > idx) bearingBetween(route.points[idx], route.points[ahead]) else null
                                            }
                                        }
                                        showLocation(p, true, routeBearing, lastSpeedKmh)
                                    } else ensureLocation()
                                    status = "Seguimiento de cámara activo"
                                },
                                shape = RoundedCornerShape(16.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF173447), contentColor = Color(0xFF67E8FF))
                            ) { Text("CENTRAR", fontSize = 8.sp, fontWeight = FontWeight.Black) }
                            Button(
                                onClick = { searchPanelOpen = !searchPanelOpen },
                                shape = RoundedCornerShape(16.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF334E86), contentColor = Color.White)
                            ) { Text(if (searchPanelOpen) "MAPA" else "BUSCAR", fontSize = 8.sp, fontWeight = FontWeight.Black) }
                            Button(
                                onClick = { voiceEnabled = !voiceEnabled; if (!voiceEnabled) tts.stop() },
                                shape = RoundedCornerShape(16.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF173447), contentColor = Color.White)
                            ) { Text(if (voiceEnabled) "VOZ" else "MUTE", fontSize = 8.sp, fontWeight = FontWeight.Black) }
                            Button(
                                onClick = { toolsExpanded = true },
                                shape = RoundedCornerShape(16.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF261F46), contentColor = Color(0xFFC8B8FF))
                            ) { Text("•••", fontSize = 13.sp, fontWeight = FontWeight.Black) }
                        }
                    }

                    if (toolsExpanded) {
                        ModalBottomSheet(
                            onDismissRequest = { toolsExpanded = false },
                            containerColor = Color(0xFF08131E),
                            contentColor = Color.White,
                            scrimColor = Color(0x66000000)
                        ) {
                            Column(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .navigationBarsPadding()
                                    .padding(horizontal = 18.dp, vertical = 8.dp)
                            ) {
                                Text("NETHERIS · NAVEGACIÓN", color = Color(0xFF66E7FF), fontSize = 10.sp, fontWeight = FontWeight.Black)
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    TextButton(onClick = { toolsExpanded = false; showRouteOverview() }) { Text("RESUMEN", color = Color(0xFF69F7C8), fontSize = 9.sp) }
                                    TextButton(onClick = { toolsExpanded = false; cycleAlternative() }) { Text("ALTERNATIVAS", color = Color(0xFF9BCFFF), fontSize = 9.sp) }
                                    TextButton(onClick = { toolsExpanded = false; searchPanelOpen = true }) { Text("NUEVA RUTA", color = Color(0xFFFFA9BC), fontSize = 9.sp) }
                                }
                            }
                        }
                    }
                }
            }
        }
        return
    }

'''

s = s.replace(anchor, landscape + anchor, 1)
s = s.replace('NetherisGPS/13.0.1 Android', 'NetherisGPS/13.1 Android')
main.write_text(s)

# In landscape hide the large outer header/session cards so the map can truly dominate the screen.
shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text()
if 'import android.content.res.Configuration\n' not in t:
    t = t.replace('import android.content.Context\n', 'import android.content.Context\nimport android.content.res.Configuration\n')
if 'import androidx.compose.ui.platform.LocalConfiguration\n' not in t:
    t = t.replace('import androidx.compose.ui.Alignment\n', 'import androidx.compose.ui.Alignment\nimport androidx.compose.ui.platform.LocalConfiguration\n')
old_column = '''                Column(modifier = Modifier.fillMaxSize()) {\n                    NetherisHeader()\n                    NavigationSessionCard()\n                    Box(modifier = Modifier.fillMaxWidth().weight(1f)) {\n                        NetherisGpsApp()\n                    }\n                }\n'''
new_column = '''                val configuration = LocalConfiguration.current\n                val landscape = configuration.orientation == Configuration.ORIENTATION_LANDSCAPE\n                Column(modifier = Modifier.fillMaxSize()) {\n                    if (!landscape) {\n                        NetherisHeader()\n                        NavigationSessionCard()\n                    }\n                    Box(modifier = Modifier.fillMaxWidth().weight(1f)) {\n                        NetherisGpsApp()\n                    }\n                }\n'''
if old_column not in t:
    raise SystemExit('shell column anchor not found')
t = t.replace(old_column, new_column, 1)
t = t.replace('NETHERIS NAVIGATION AI · V13.0.1', 'NETHERIS NAVIGATION AI · V13.1')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 131', 'versionCode = 132').replace('versionName = "13.0.1"', 'versionName = "13.1.0"')
build.write_text(b)

print('Applied Netheris GPS v13.1 full-screen landscape overlay')
