from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# Imports for Android-safe bottom dock and Material bottom sheet.
if 'import androidx.compose.foundation.layout.navigationBarsPadding\n' not in s:
    s = s.replace(
        'import androidx.compose.foundation.layout.height\n',
        'import androidx.compose.foundation.layout.height\nimport androidx.compose.foundation.layout.navigationBarsPadding\n'
    )
if 'import androidx.compose.material3.ModalBottomSheet\n' not in s:
    s = s.replace(
        'import androidx.compose.material3.MaterialTheme\n',
        'import androidx.compose.material3.MaterialTheme\nimport androidx.compose.material3.ModalBottomSheet\n'
    )

# Replace the old inline dock + expandable tools area with an adaptive dock and a true bottom sheet.
dock_start_marker = '''                Spacer(Modifier.height(7.dp))\n                Surface(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(21.dp), color = Color(0xFF081722)) {\n'''
dock_start = s.find(dock_start_marker)
if dock_start < 0:
    raise SystemExit('v8/v9 dock start not found')

ui_end_marker = '''\n            }\n        }\n    }\n}\n\n@Composable\nprivate fun NetherisMap'''
ui_end = s.find(ui_end_marker, dock_start)
if ui_end < 0:
    raise SystemExit('UI end marker not found')

new_tail = r'''                Spacer(Modifier.height(7.dp))
                Surface(
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding(),
                    shape = RoundedCornerShape(24.dp),
                    color = Color(0xF20A1823),
                    shadowElevation = 8.dp
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 7.dp, vertical = 7.dp),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        when {
                            immersiveMode -> {
                                Button(
                                    onClick = { resetToExploration() },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(17.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF54263B), contentColor = Color.White)
                                ) { Text("DETENER", fontSize = 9.sp, fontWeight = FontWeight.Black) }
                                Button(
                                    onClick = { voiceEnabled = !voiceEnabled; if (!voiceEnabled) tts.stop() },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(17.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF173447), contentColor = Color(0xFF67E8FF))
                                ) { Text(if (voiceEnabled) "VOZ" else "MUTE", fontSize = 9.sp, fontWeight = FontWeight.Black) }
                                Button(
                                    onClick = { lastLocation?.let { showLocation(it, true) } ?: ensureLocation() },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(17.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF173447), contentColor = Color.White)
                                ) { Text("CENTRAR", fontSize = 9.sp, fontWeight = FontWeight.Black) }
                            }
                            activeRoute != null -> {
                                Button(
                                    onClick = { startNavigation() },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(17.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF315B91), contentColor = Color.White)
                                ) { Text("INICIAR", fontSize = 9.sp, fontWeight = FontWeight.Black) }
                                Button(
                                    onClick = { cycleAlternative() },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(17.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF15594F), contentColor = Color.White)
                                ) { Text("ALT", fontSize = 9.sp, fontWeight = FontWeight.Black) }
                                Button(
                                    onClick = {
                                        val d = destination
                                        if (d != null) addFavorite(d) else status = "Selecciona destino"
                                    },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(17.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF5A4B20), contentColor = Color(0xFFFFE39A))
                                ) { Text("GUARDAR", fontSize = 9.sp, fontWeight = FontWeight.Black) }
                            }
                            else -> {
                                Button(
                                    onClick = { ensureLocation() },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(17.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF143545), contentColor = Color(0xFF63E7FF))
                                ) { Text("UBICACIÓN", fontSize = 8.sp, fontWeight = FontWeight.Black) }
                                Button(
                                    onClick = { calculateRoutes() },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(17.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0E6559), contentColor = Color.White)
                                ) { Text("RUTA", fontSize = 9.sp, fontWeight = FontWeight.Black) }
                                Button(
                                    onClick = { startNavigation() },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(17.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF315B91), contentColor = Color.White)
                                ) { Text("NAVEGAR", fontSize = 8.sp, fontWeight = FontWeight.Black) }
                            }
                        }

                        Button(
                            onClick = { toolsExpanded = true },
                            shape = RoundedCornerShape(17.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF261F46), contentColor = Color(0xFFC8B8FF))
                        ) { Text("•••", fontSize = 14.sp, fontWeight = FontWeight.Black) }
                    }
                }

                if (toolsExpanded) {
                    ModalBottomSheet(
                        onDismissRequest = { toolsExpanded = false },
                        containerColor = Color(0xFF08131E),
                        contentColor = Color.White,
                        scrimColor = Color(0x99000000)
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .navigationBarsPadding()
                                .padding(horizontal = 18.dp, vertical = 8.dp)
                        ) {
                            Text("NETHERIS · MÁS", color = Color(0xFF66E7FF), fontSize = 11.sp, fontWeight = FontWeight.Black)
                            Text("Acciones, lugares y viajes", color = Color(0xFF7F98AA), fontSize = 9.sp)
                            Spacer(Modifier.height(8.dp))

                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                TextButton(onClick = { toolsExpanded = false; cycleAlternative() }) { Text("ALTERNATIVAS", color = Color(0xFF9BCFFF), fontSize = 9.sp) }
                                TextButton(onClick = { if (demoActive) resetToExploration() else startDemo(); toolsExpanded = false }) { Text(if (demoActive) "STOP DEMO" else "DEMO", color = Color(0xFFC7AEFF), fontSize = 9.sp) }
                                TextButton(onClick = { voiceEnabled = !voiceEnabled; if (!voiceEnabled) tts.stop() }) { Text(if (voiceEnabled) "VOZ ON" else "VOZ OFF", color = Color(0xFF66E7FF), fontSize = 9.sp) }
                            }

                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                TextButton(onClick = {
                                    toolsExpanded = false
                                    if (prefs.contains(HOME_LAT)) {
                                        selectDestination(SearchResult(LatLng(prefs.getLong(HOME_LAT, 0L).let(Double::fromBits), prefs.getLong(HOME_LON, 0L).let(Double::fromBits)), "Casa · Netheris"))
                                    } else status = "Casa no guardada"
                                }) { Text("CASA", color = Color.White, fontSize = 9.sp) }
                                TextButton(onClick = {
                                    val d = destination
                                    if (d != null) addFavorite(d) else status = "Selecciona destino"
                                }) { Text("★ GUARDAR", color = Color(0xFFFFDF78), fontSize = 9.sp) }
                                TextButton(onClick = {
                                    toolsExpanded = false
                                    resetToExploration()
                                    destinationMarker?.let { map?.removeMarker(it) }
                                    destinationMarker = null
                                    destination = null
                                    searchText = ""
                                    status = "Katherine lista · busca un nuevo destino"
                                }) { Text("NUEVA RUTA", color = Color(0xFFFFA9BC), fontSize = 9.sp) }
                            }

                            if (favorites.isNotEmpty()) {
                                Spacer(Modifier.height(5.dp))
                                Text("FAVORITOS", color = Color(0xFFFFD76A), fontSize = 9.sp, fontWeight = FontWeight.Black)
                                favorites.take(4).forEach { fav ->
                                    TextButton(
                                        onClick = { toolsExpanded = false; selectDestination(fav) },
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        Text("★ ${fav.label}", color = Color(0xFFFFE8A8), fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                    }
                                }
                            }

                            if (tripHistory.isNotEmpty()) {
                                Spacer(Modifier.height(4.dp))
                                Text("ÚLTIMOS VIAJES", color = Color(0xFF66E7FF), fontSize = 9.sp, fontWeight = FontWeight.Black)
                                tripHistory.take(4).forEach { trip ->
                                    TextButton(
                                        onClick = { toolsExpanded = false; selectDestination(trip) },
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        Text("↺ ${trip.label}", color = Color(0xFFA8BECD), fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                    }
                                }
                            }

                            Spacer(Modifier.height(5.dp))
                            TextButton(
                                onClick = {
                                    val save: (LatLng) -> Unit = { p ->
                                        prefs.edit().putLong(HOME_LAT, p.latitude.toBits()).putLong(HOME_LON, p.longitude.toBits()).apply()
                                        showHome(p, false)
                                        status = "Casa guardada"
                                    }
                                    lastLocation?.let(save) ?: requestLocation { it?.let(save) }
                                },
                                modifier = Modifier.fillMaxWidth()
                            ) { Text("GUARDAR UBICACIÓN ACTUAL COMO CASA", color = Color(0xFF9EB6C8), fontSize = 9.sp) }
                        }
                    }
                }
'''

s = s[:dock_start] + new_tail + s[ui_end:]
s = s.replace('NetherisGPS/9.0 Android', 'NetherisGPS/9.1 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text().replace('NETHERIS NAVIGATION AI · V9.0', 'NETHERIS NAVIGATION AI · V9.1')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 90', 'versionCode = 91').replace('versionName = "9.0.0"', 'versionName = "9.1.0"')
build.write_text(b)

print('Applied Netheris GPS v9.1 adaptive dock + bottom sheet')
