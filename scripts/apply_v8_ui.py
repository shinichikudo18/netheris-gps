from pathlib import Path

path = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
text = path.read_text()
start = text.index('    MaterialTheme(colorScheme = NetherisColors) {')
end = text.index('\n@Composable\nprivate fun NetherisMap(', start)

new_block = r'''    var toolsExpanded by remember { mutableStateOf(false) }

    val immersiveMode = navigationActive || demoActive
    val assistantState = when {
        status.contains("Recalculando", ignoreCase = true) -> "RECALCULANDO"
        status.contains("Buscando", ignoreCase = true) -> "BUSCANDO DESTINO"
        demoActive -> "SIMULACIÓN ACTIVA"
        navigationActive -> "GUIANDO"
        activeRoute != null -> "RUTA PREPARADA"
        else -> "LISTA"
    }

    MaterialTheme(colorScheme = NetherisColors) {
        Surface(modifier = Modifier.fillMaxSize(), color = Color(0xFF030811)) {
            Column(modifier = Modifier.fillMaxSize().padding(horizontal = 9.dp, vertical = 4.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text("KATHERINE · $assistantState", color = Color(0xFF5FE7FF), fontSize = 10.sp, fontWeight = FontWeight.Black)
                        Text(status, color = Color(0xFF7F98AA), fontSize = 9.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    }
                    Text(
                        when {
                            demoActive -> "DEMO"
                            navigationActive -> "NAV"
                            activeRoute != null -> "ROUTE"
                            else -> "READY"
                        },
                        color = if (immersiveMode) Color(0xFF69F7C8) else Color(0xFFB49BFF),
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Black
                    )
                }

                if (immersiveMode || activeRoute != null || nextInstruction.isNotEmpty()) {
                    Spacer(Modifier.height(5.dp))
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(18.dp),
                        color = Color(0xEC081824),
                        shadowElevation = 4.dp
                    ) {
                        Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 9.dp)) {
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(
                                    nextInstruction.ifBlank { if (immersiveMode) "Katherine está siguiendo la ruta" else "Ruta preparada" },
                                    color = Color.White,
                                    fontSize = if (immersiveMode) 17.sp else 15.sp,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.fillMaxWidth(0.78f),
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis
                                )
                                Text(nextDistance, color = Color(0xFF5FE7FF), fontSize = 17.sp, fontWeight = FontWeight.Black)
                            }
                            if (activeRoute != null) {
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    "$remainingInfo restante   ·   ETA $etaInfo   ·   $speedInfo",
                                    color = Color(0xFFA6C0D2),
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }
                    }
                }

                if (!immersiveMode) {
                    Spacer(Modifier.height(6.dp))
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(19.dp),
                        color = Color(0xFF08141F)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(5.dp),
                            horizontalArrangement = Arrangement.spacedBy(5.dp)
                        ) {
                            OutlinedTextField(
                                value = searchText,
                                onValueChange = { searchText = it },
                                modifier = Modifier.fillMaxWidth(0.82f),
                                singleLine = true,
                                label = { Text("¿A dónde vamos?") }
                            )
                            Button(
                                onClick = { findDestination() },
                                shape = RoundedCornerShape(16.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF5FE7FF), contentColor = Color(0xFF031018))
                            ) { Text("⌕", fontSize = 18.sp, fontWeight = FontWeight.Black) }
                        }
                    }

                    if (searchResults.isNotEmpty()) {
                        Spacer(Modifier.height(3.dp))
                        Surface(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(14.dp), color = Color(0xFF091722)) {
                            Column(modifier = Modifier.padding(vertical = 2.dp)) {
                                searchResults.take(3).forEach { result ->
                                    TextButton(onClick = { selectDestination(result) }, modifier = Modifier.fillMaxWidth()) {
                                        Text("◇ ${result.label}", maxLines = 1, overflow = TextOverflow.Ellipsis, color = Color(0xFFDCEEFF), fontSize = 11.sp)
                                    }
                                }
                            }
                        }
                    } else if (destination == null && recents.isNotEmpty()) {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                            recents.take(2).forEach { recent ->
                                TextButton(onClick = { selectDestination(recent) }) {
                                    Text("⌁ ${recent.label.substringBefore(",").take(20)}", color = Color(0xFF829BAD), fontSize = 10.sp)
                                }
                            }
                        }
                    }
                }

                Spacer(Modifier.height(5.dp))
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(22.dp),
                    color = Color(0xFF06101A),
                    shadowElevation = 6.dp
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(
                                when {
                                    immersiveMode -> 500.dp
                                    activeRoute != null -> 315.dp
                                    searchResults.isNotEmpty() -> 300.dp
                                    else -> 385.dp
                                }
                            )
                    ) {
                        NetherisMap(
                            modifier = Modifier.fillMaxSize(),
                            onMapReady = { readyMap ->
                                map = readyMap
                                status = "Mapa listo · mantén pulsado para fijar destino"
                                if (prefs.contains(HOME_LAT) && prefs.contains(HOME_LON)) showHome(LatLng(prefs.getLong(HOME_LAT, 0L).let(Double::fromBits), prefs.getLong(HOME_LON, 0L).let(Double::fromBits)), false)
                                if (prefs.contains(FAVORITE_LAT) && prefs.contains(FAVORITE_LON)) showFavorite(LatLng(prefs.getLong(FAVORITE_LAT, 0L).let(Double::fromBits), prefs.getLong(FAVORITE_LON, 0L).let(Double::fromBits)), prefs.getString(FAVORITE_LABEL, "Favorito") ?: "Favorito", false)
                            },
                            onLongPress = { point -> selectDestination(SearchResult(point, "Punto en mapa"), false) }
                        )
                    }
                }

                Spacer(Modifier.height(7.dp))
                Surface(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(21.dp), color = Color(0xFF081722)) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 6.dp, vertical = 6.dp),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Button(
                            onClick = { ensureLocation() },
                            shape = RoundedCornerShape(15.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF113141), contentColor = Color(0xFF5FE7FF))
                        ) { Text("⌖", fontSize = 16.sp) }
                        Button(
                            onClick = { calculateRoutes() },
                            shape = RoundedCornerShape(15.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0D665B), contentColor = Color.White)
                        ) { Text("RUTA", fontSize = 10.sp, fontWeight = FontWeight.Black) }
                        Button(
                            onClick = { if (navigationActive && !demoActive) stopNavigation() else startNavigation() },
                            shape = RoundedCornerShape(15.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = if (navigationActive && !demoActive) Color(0xFF57263C) else Color(0xFF314D84), contentColor = Color.White)
                        ) { Text(if (navigationActive && !demoActive) "DETENER" else "NAVEGAR", fontSize = 10.sp, fontWeight = FontWeight.Black) }
                        Button(
                            onClick = { toolsExpanded = !toolsExpanded },
                            shape = RoundedCornerShape(15.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF211B3E), contentColor = Color(0xFFC1B0FF))
                        ) { Text(if (toolsExpanded) "×" else "•••", fontSize = 14.sp, fontWeight = FontWeight.Black) }
                    }
                }

                if (toolsExpanded) {
                    Spacer(Modifier.height(5.dp))
                    Surface(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp), color = Color(0xFF07121C)) {
                        Column(modifier = Modifier.padding(5.dp)) {
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                TextButton(onClick = { cycleAlternative() }) { Text("ALT", color = Color(0xFF8FCBFF), fontSize = 10.sp) }
                                TextButton(onClick = { if (demoActive) stopNavigation() else startDemo() }) { Text(if (demoActive) "STOP DEMO" else "DEMO", color = Color(0xFFC5A9FF), fontSize = 10.sp) }
                                TextButton(onClick = { voiceEnabled = !voiceEnabled; if (!voiceEnabled) tts.stop() }) { Text(if (voiceEnabled) "VOZ ON" else "VOZ OFF", color = Color(0xFF5FE7FF), fontSize = 10.sp) }
                                TextButton(onClick = { if (nextInstruction.isNotBlank()) speak(nextInstruction) else speak("Katherine lista para navegar") }) { Text("REPETIR", color = Color.White, fontSize = 10.sp) }
                            }
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                TextButton(onClick = {
                                    if (prefs.contains(HOME_LAT)) selectDestination(SearchResult(LatLng(prefs.getLong(HOME_LAT, 0L).let(Double::fromBits), prefs.getLong(HOME_LON, 0L).let(Double::fromBits)), "Casa · Netheris")) else status = "Casa no guardada"
                                }) { Text("CASA", color = Color.White, fontSize = 10.sp) }
                                TextButton(onClick = {
                                    val d = destination ?: run { status = "Selecciona destino"; return@TextButton }
                                    prefs.edit().putLong(FAVORITE_LAT, d.point.latitude.toBits()).putLong(FAVORITE_LON, d.point.longitude.toBits()).putString(FAVORITE_LABEL, d.label.substringBefore(",")).apply()
                                    showFavorite(d.point, d.label.substringBefore(","), false); status = "Favorito guardado"
                                }) { Text("★ GUARDAR", color = Color(0xFFFFD76A), fontSize = 10.sp) }
                                TextButton(onClick = {
                                    if (prefs.contains(FAVORITE_LAT)) selectDestination(SearchResult(LatLng(prefs.getLong(FAVORITE_LAT, 0L).let(Double::fromBits), prefs.getLong(FAVORITE_LON, 0L).let(Double::fromBits)), prefs.getString(FAVORITE_LABEL, "Favorito") ?: "Favorito")) else status = "Sin favorito"
                                }) { Text("★ IR", color = Color(0xFFFFD76A), fontSize = 10.sp) }
                                TextButton(onClick = {
                                    stopNavigation(); routePolyline?.let { map?.removePolyline(it) }; routePolyline = null; destinationMarker?.let { map?.removeMarker(it) }; destinationMarker = null; destination = null; activeRoute = null; routeOptions = emptyList(); searchResults = emptyList(); nextInstruction = ""; nextDistance = ""; remainingInfo = ""; speedInfo = "0 km/h"; etaInfo = "--:--"; status = "Ruta limpiada"
                                }) { Text("LIMPIAR", color = Color(0xFFFFA9BC), fontSize = 10.sp) }
                            }
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                                TextButton(onClick = {
                                    val save: (LatLng) -> Unit = { p -> prefs.edit().putLong(HOME_LAT, p.latitude.toBits()).putLong(HOME_LON, p.longitude.toBits()).apply(); showHome(p, false); status = "Casa guardada" }
                                    lastLocation?.let(save) ?: requestLocation { it?.let(save) }
                                }) { Text("GUARDAR UBICACIÓN COMO CASA", color = Color(0xFF9DB4C7), fontSize = 9.sp) }
                            }
                        }
                    }
                }
            }
        }
    }
}
'''

text = text[:start] + new_block + text[end:]
text = text.replace('NetherisGPS/1.8 Android', 'NetherisGPS/8.0 Android')
path.write_text(text)
print('Applied Netheris GPS v8 immersive UI')
