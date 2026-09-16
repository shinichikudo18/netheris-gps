from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# Katherine avatar inside arrival experience.
if 'import cl.netheris.gps.ui.KatherineAvatar\n' not in s:
    s = s.replace(
        'import cl.netheris.gps.nav.NavigationForegroundService\n',
        'import cl.netheris.gps.nav.NavigationForegroundService\nimport cl.netheris.gps.ui.KatherineAvatar\n'
    )

# Smart camera / arrival state.
state_anchor = '    var toolsExpanded by remember { mutableStateOf(false) }\n'
if state_anchor not in s:
    raise SystemExit('toolsExpanded state anchor not found')
s = s.replace(
    state_anchor,
    state_anchor +
    '    var cameraFollowEnabled by remember { mutableStateOf(true) }\n'
    '    var lastSpeedKmh by remember { mutableStateOf(0f) }\n'
    '    var arrivalVisible by remember { mutableStateOf(false) }\n'
    '    var arrivedDestination by remember { mutableStateOf<SearchResult?>(null) }\n'
)

# Camera follows intelligently and changes zoom according to speed.
old_show = '''    fun showLocation(latLng: LatLng, moveCamera: Boolean = true, bearing: Float? = null) {\n        val readyMap = map ?: return\n        locationMarker?.let { readyMap.removeMarker(it) }\n        locationMarker = readyMap.addMarker(MarkerOptions().position(latLng).title(if (demoActive) "Demo" else "Mi ubicación"))\n        if (moveCamera) {\n            val builder = CameraPosition.Builder().target(latLng).zoom(if (navigationActive || demoActive) 17.2 else 16.5)\n            if (navigationActive || demoActive) {\n                builder.tilt(48.0)\n                if (bearing != null && !bearing.isNaN()) builder.bearing(bearing.toDouble())\n            }\n            readyMap.animateCamera(CameraUpdateFactory.newCameraPosition(builder.build()), 350)\n        }\n        lastLocation = latLng\n    }\n'''
new_show = '''    fun showLocation(\n        latLng: LatLng,\n        moveCamera: Boolean = true,\n        bearing: Float? = null,\n        speedKmh: Float? = null\n    ) {\n        val readyMap = map ?: return\n        locationMarker?.let { readyMap.removeMarker(it) }\n        locationMarker = readyMap.addMarker(MarkerOptions().position(latLng).title(if (demoActive) "Demo" else "Mi ubicación"))\n        val isNav = navigationActive || demoActive\n        val shouldFollow = moveCamera && (!isNav || cameraFollowEnabled)\n        if (shouldFollow) {\n            val speed = speedKmh ?: lastSpeedKmh\n            val zoom = if (!isNav) 16.5 else when {\n                speed >= 90f -> 15.25\n                speed >= 65f -> 15.65\n                speed >= 40f -> 16.05\n                speed >= 20f -> 16.55\n                speed >= 8f -> 16.95\n                else -> 17.30\n            }\n            val builder = CameraPosition.Builder().target(latLng).zoom(zoom)\n            if (isNav) {\n                builder.tilt(if (speed >= 20f) 50.0 else 43.0)\n                if (bearing != null && !bearing.isNaN()) builder.bearing(bearing.toDouble())\n            }\n            readyMap.animateCamera(CameraUpdateFactory.newCameraPosition(builder.build()), 320)\n        }\n        lastLocation = latLng\n    }\n'''
if old_show not in s:
    raise SystemExit('showLocation anchor not found')
s = s.replace(old_show, new_show)

# Keep latest speed for auto zoom and recenter.
s = s.replace(
    '        speedInfo = "${speedKmh.toInt().coerceAtLeast(0)} km/h"\n',
    '        lastSpeedKmh = speedKmh.coerceAtLeast(0f)\n        speedInfo = "${speedKmh.toInt().coerceAtLeast(0)} km/h"\n'
)

# Navigation always begins in follow-camera mode and closes stale arrival panel.
start_anchor = '        stopNavigation(); navigationActive = true; status = "Navegando"; speak("Navegación iniciada")\n'
if start_anchor not in s:
    raise SystemExit('startNavigation activation anchor not found')
s = s.replace(
    start_anchor,
    '        stopNavigation(); cameraFollowEnabled = true; arrivalVisible = false; navigationActive = true; status = "Navegando"; speak("Navegación iniciada")\n'
)

# Pass speed into camera updates during live navigation.
s = s.replace(
    '            showLocation(point, true, if (location.hasBearing()) location.bearing else null)\n            updateProgress(point, speed)\n',
    '            showLocation(point, true, if (location.hasBearing()) location.bearing else null, speed)\n            updateProgress(point, speed)\n'
)

# Natural arrival -> store trip, stop both navigation layers, then show Netheris arrival sheet.
old_arrival = '                remainingInfo = "0 m"; nextInstruction = "Llegaste al destino 🎉"; nextDistance = ""; destination?.let { recordTrip(it) }; speak("Llegaste al destino"); resetToExploration(); status = "Destino alcanzado · listo para nueva ruta"\n'
new_arrival = '                remainingInfo = "0 m"; nextInstruction = "Llegaste al destino 🎉"; nextDistance = ""; destination?.let { recordTrip(it); arrivedDestination = it }; speak("Llegaste al destino"); resetToExploration(); arrivalVisible = true; status = "Destino alcanzado · viaje guardado"\n'
if old_arrival not in s:
    raise SystemExit('v9 natural arrival anchor not found')
s = s.replace(old_arrival, new_arrival)

# Demo uses the same camera zoom behavior and arrival UX, but is not recorded as a real trip.
s = s.replace(
    '            showLocation(point, true, bearingBetween(point, current.points[next]))\n            updateProgress(point, 42f)\n',
    '            showLocation(point, true, bearingBetween(point, current.points[next]), 42f)\n            updateProgress(point, 42f)\n'
)
s = s.replace(
    'showLocation(current.points.last(), true); remainingInfo = "0 m"; nextInstruction = "Llegaste al destino 🎉"; nextDistance = ""; speak("Llegaste al destino"); demoActive = false; navigationActive = false; toolsExpanded = false; status = "DEMO finalizada · listo para nueva ruta"; return@Runnable',
    'showLocation(current.points.last(), true, null, 0f); remainingInfo = "0 m"; nextInstruction = "Llegaste al destino 🎉"; nextDistance = ""; destination?.let { arrivedDestination = it }; speak("Llegaste al destino"); demoActive = false; navigationActive = false; cameraFollowEnabled = true; toolsExpanded = false; arrivalVisible = true; status = "DEMO finalizada"; return@Runnable'
)

# Reset camera state whenever the session is fully reset.
reset_anchor = '''    fun resetToExploration() {\n        stopNavigation()\n        runCatching {\n'''
if reset_anchor not in s:
    raise SystemExit('resetToExploration anchor not found')
s = s.replace(
    reset_anchor,
    '''    fun resetToExploration() {\n        stopNavigation()\n        cameraFollowEnabled = true\n        lastSpeedKmh = 0f\n        runCatching {\n'''
)

# Detect manual camera gestures. Programmatic camera animations do not disable follow.
map_ready_anchor = '''                            onMapReady = { readyMap ->\n                                map = readyMap\n                                status = "Mapa listo · mantén pulsado para fijar destino"\n'''
if map_ready_anchor not in s:
    raise SystemExit('onMapReady anchor not found')
s = s.replace(
    map_ready_anchor,
    '''                            onMapReady = { readyMap ->\n                                map = readyMap\n                                readyMap.addOnCameraMoveStartedListener { reason ->\n                                    if ((navigationActive || demoActive) && reason == MapLibreMap.OnCameraMoveStartedListener.REASON_API_GESTURE) {\n                                        cameraFollowEnabled = false\n                                        status = "Mapa libre · toca CENTRAR para seguir a Katherine"\n                                    }\n                                }\n                                status = "Mapa listo · mantén pulsado para fijar destino"\n'''
)

# Recenter dock action resumes follow mode instead of doing a one-off jump.
old_center = '                                    onClick = { lastLocation?.let { showLocation(it, true) } ?: ensureLocation() },\n'
new_center = '                                    onClick = { cameraFollowEnabled = true; lastLocation?.let { showLocation(it, true, null, lastSpeedKmh) } ?: ensureLocation(); status = "Seguimiento de cámara activo" },\n'
if old_center not in s:
    raise SystemExit('v9.1 center button anchor not found')
s = s.replace(old_center, new_center)

# Arrival bottom sheet. Insert before the tools bottom sheet.
tools_sheet_anchor = '''                if (toolsExpanded) {\n                    ModalBottomSheet(\n'''
if tools_sheet_anchor not in s:
    raise SystemExit('tools bottom sheet anchor not found')
arrival_sheet = r'''                if (arrivalVisible) {
                    ModalBottomSheet(
                        onDismissRequest = { arrivalVisible = false },
                        containerColor = Color(0xFF06131E),
                        contentColor = Color.White,
                        scrimColor = Color(0xB0000000)
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .navigationBarsPadding()
                                .padding(horizontal = 20.dp, vertical = 10.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            KatherineAvatar(size = 72.dp)
                            Spacer(Modifier.height(8.dp))
                            Text("DESTINO ALCANZADO", color = Color(0xFF66E7FF), fontSize = 12.sp, fontWeight = FontWeight.Black)
                            Text(
                                arrivedDestination?.label?.substringBefore(",") ?: "Llegamos",
                                color = Color.White,
                                fontSize = 21.sp,
                                fontWeight = FontWeight.Black,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis
                            )
                            Text("Katherine completó la navegación", color = Color(0xFF94ADBE), fontSize = 10.sp)
                            Spacer(Modifier.height(12.dp))
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                                Button(
                                    onClick = {
                                        arrivalVisible = false
                                        arrivedDestination = null
                                        destinationMarker?.let { map?.removeMarker(it) }
                                        destinationMarker = null
                                        destination = null
                                        searchText = ""
                                        status = "Katherine lista · busca un nuevo destino"
                                    },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(17.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF13685D), contentColor = Color.White)
                                ) { Text("NUEVA RUTA", fontSize = 9.sp, fontWeight = FontWeight.Black) }

                                Button(
                                    onClick = {
                                        if (prefs.contains(HOME_LAT) && prefs.contains(HOME_LON)) {
                                            arrivalVisible = false
                                            arrivedDestination = null
                                            val home = SearchResult(
                                                LatLng(
                                                    prefs.getLong(HOME_LAT, 0L).let(Double::fromBits),
                                                    prefs.getLong(HOME_LON, 0L).let(Double::fromBits)
                                                ),
                                                "Casa · Netheris"
                                            )
                                            selectDestination(home)
                                            startNavigation()
                                        } else {
                                            status = "Casa no guardada"
                                        }
                                    },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(17.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF334E86), contentColor = Color.White)
                                ) { Text("IR A CASA", fontSize = 9.sp, fontWeight = FontWeight.Black) }

                                Button(
                                    onClick = {
                                        arrivalVisible = false
                                        arrivedDestination = null
                                        status = "Katherine lista"
                                    },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(17.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF202B36), contentColor = Color(0xFFBCD0DD))
                                ) { Text("CERRAR", fontSize = 9.sp, fontWeight = FontWeight.Black) }
                            }
                            Spacer(Modifier.height(8.dp))
                        }
                    }
                }

'''
s = s.replace(tools_sheet_anchor, arrival_sheet + tools_sheet_anchor)

# Version strings.
s = s.replace('NetherisGPS/9.1 Android', 'NetherisGPS/10.0 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text().replace('NETHERIS NAVIGATION AI · V9.1', 'NETHERIS NAVIGATION AI · V10.0')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 91', 'versionCode = 100').replace('versionName = "9.1.0"', 'versionName = "10.0.0"')
build.write_text(b)

print('Applied Netheris GPS v10 smart camera + speed zoom + arrival experience')
