from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# Landscape + adaptive UI imports.
if 'import android.content.res.Configuration\n' not in s:
    s = s.replace('import android.content.Context\n', 'import android.content.Context\nimport android.content.res.Configuration\n')
if 'import androidx.compose.ui.platform.LocalConfiguration\n' not in s:
    s = s.replace('import androidx.compose.ui.platform.LocalContext\n', 'import androidx.compose.ui.platform.LocalConfiguration\nimport androidx.compose.ui.platform.LocalContext\n')

# Work location persistence.
const_anchor = 'private const val HOME_LON = "home_lon"\n'
if const_anchor not in s:
    raise SystemExit('HOME_LON anchor not found')
s = s.replace(
    const_anchor,
    const_anchor + 'private const val WORK_LAT = "work_lat"\nprivate const val WORK_LON = "work_lon"\n'
)

# Route parser must aggregate steps across all legs when a waypoint is present.
old_legs = '''    val legs = route.optJSONArray("legs")\n    if (legs != null && legs.length() > 0) {\n        val rawSteps = legs.getJSONObject(0).optJSONArray("steps")\n        if (rawSteps != null) {\n            for (i in 0 until rawSteps.length()) {\n                val step = rawSteps.getJSONObject(i)\n                val location = step.optJSONObject("maneuver")?.optJSONArray("location") ?: continue\n                if (location.length() >= 2) {\n                    val point = LatLng(location.getDouble(1), location.getDouble(0))\n                    steps.add(RouteStep(instructionFor(step), point, nearestRouteIndex(point, points)))\n                }\n            }\n        }\n    }\n'''
new_legs = '''    val legs = route.optJSONArray("legs")\n    if (legs != null) {\n        for (legIndex in 0 until legs.length()) {\n            val rawSteps = legs.getJSONObject(legIndex).optJSONArray("steps") ?: continue\n            for (i in 0 until rawSteps.length()) {\n                val step = rawSteps.getJSONObject(i)\n                val location = step.optJSONObject("maneuver")?.optJSONArray("location") ?: continue\n                if (location.length() >= 2) {\n                    val point = LatLng(location.getDouble(1), location.getDouble(0))\n                    steps.add(RouteStep(instructionFor(step), point, nearestRouteIndex(point, points)))\n                }\n            }\n        }\n    }\n'''
if old_legs not in s:
    raise SystemExit('route leg parser anchor not found')
s = s.replace(old_legs, new_legs, 1)

# Optional intermediate waypoint. Existing callers continue to work via default null.
old_fetch = '''private fun fetchRoutes(origin: LatLng, destination: LatLng): List<RouteResult> {\n    val url = "https://router.project-osrm.org/route/v1/driving/" +\n        "${origin.longitude},${origin.latitude};${destination.longitude},${destination.latitude}" +\n        "?overview=full&geometries=geojson&steps=true&alternatives=2"\n'''
new_fetch = '''private fun fetchRoutes(origin: LatLng, destination: LatLng, via: LatLng? = null): List<RouteResult> {\n    val coordinates = if (via == null) {\n        "${origin.longitude},${origin.latitude};${destination.longitude},${destination.latitude}"\n    } else {\n        "${origin.longitude},${origin.latitude};${via.longitude},${via.latitude};${destination.longitude},${destination.latitude}"\n    }\n    val url = "https://router.project-osrm.org/route/v1/driving/" + coordinates +\n        "?overview=full&geometries=geojson&steps=true&alternatives=2"\n'''
if old_fetch not in s:
    raise SystemExit('fetchRoutes anchor not found')
s = s.replace(old_fetch, new_fetch, 1)

# State: landscape, waypoint mode and early voice cue.
state_anchor = '    val locationManager = remember { context.getSystemService(Context.LOCATION_SERVICE) as LocationManager }\n'
if state_anchor not in s:
    raise SystemExit('locationManager anchor not found')
s = s.replace(
    state_anchor,
    state_anchor + '    val configuration = LocalConfiguration.current\n    val isLandscape = configuration.orientation == Configuration.ORIENTATION_LANDSCAPE\n'
)

voice_state_anchor = '    var lastSpokenFarStep by remember { mutableStateOf(-1) }\n'
if voice_state_anchor not in s:
    raise SystemExit('voice state anchor not found')
s = s.replace(
    voice_state_anchor,
    voice_state_anchor + '    var lastSpokenPreviewStep by remember { mutableStateOf(-1) }\n'
)

destination_state_anchor = '    var destination by remember { mutableStateOf<SearchResult?>(null) }\n'
if destination_state_anchor not in s:
    raise SystemExit('destination state anchor not found')
s = s.replace(
    destination_state_anchor,
    destination_state_anchor + '    var waypoint by remember { mutableStateOf<SearchResult?>(null) }\n    var addingStop by remember { mutableStateOf(false) }\n'
)

# Selecting a search result while in stop mode adds/replaces the intermediate stop.
select_anchor = '''    fun selectDestination(result: SearchResult, moveCamera: Boolean = true) {\n        val readyMap = map ?: return\n'''
if select_anchor not in s:
    raise SystemExit('selectDestination anchor not found')
s = s.replace(
    select_anchor,
    '''    fun selectDestination(result: SearchResult, moveCamera: Boolean = true) {\n        val readyMap = map ?: return\n        if (addingStop && destination != null) {\n            waypoint = result\n            addingStop = false\n            searchResults = emptyList()\n            routeOptions = emptyList()\n            activeRoute = null\n            selectedRouteIndex = 0\n            status = "Parada agregada · ${result.label.substringBefore(",")}"\n            if (moveCamera) readyMap.cameraPosition = CameraPosition.Builder().target(result.point).zoom(15.5).build()\n            return\n        }\n''',
    1
)

# New final destination clears any stale waypoint unless the user is explicitly adding a stop.
select_reset_anchor = '        destination = result\n        searchResults = emptyList()\n'
if select_reset_anchor not in s:
    raise SystemExit('destination assignment anchor not found')
s = s.replace(select_reset_anchor, '        destination = result\n        waypoint = null\n        addingStop = false\n        searchResults = emptyList()\n', 1)

# Route calculations use the optional stop.
s = s.replace('val routes = fetchRoutes(origin, dest.point)', 'val routes = fetchRoutes(origin, dest.point, waypoint?.point)')

# Reset preview voice state when drawing a new route.
reset_voice_anchor = '        lastSpokenFarStep = -1\n        lastSpokenNearStep = -1\n'
if reset_voice_anchor not in s:
    raise SystemExit('spoken state reset anchor not found')
s = s.replace(reset_voice_anchor, '        lastSpokenPreviewStep = -1\n        lastSpokenFarStep = -1\n        lastSpokenNearStep = -1\n', 1)

# Three-stage voice guidance: preview ~1 km, prepare ~300 m, execute ~70 m.
far_voice_anchor = '''        if (index != lastSpokenFarStep && toManeuver in 120f..450f) {\n            speak("En ${formatDistance(toManeuver)}, ${step.instruction.lowercase(Locale.getDefault())}")\n            lastSpokenFarStep = index\n        }\n'''
if far_voice_anchor not in s:
    raise SystemExit('far voice anchor not found')
s = s.replace(
    far_voice_anchor,
    '''        if (index != lastSpokenPreviewStep && toManeuver in 700f..1200f) {\n            speak("En aproximadamente ${formatDistance(toManeuver)}, ${step.instruction.lowercase(Locale.getDefault())}")\n            lastSpokenPreviewStep = index\n        }\n        if (index != lastSpokenFarStep && toManeuver in 120f..450f) {\n            speak("En ${formatDistance(toManeuver)}, ${step.instruction.lowercase(Locale.getDefault())}")\n            lastSpokenFarStep = index\n        }\n''',
    1
)

# Smarter reroute: account for reported GPS accuracy to avoid false deviations.
reroute_anchor = '''            val current = activeRoute\n            if (current != null && distanceToRoute(point, current.points) > OFF_ROUTE_METERS && SystemClock.elapsedRealtime() - lastRerouteAt > 22000L) recalculateFrom(point)\n            else status = "Navegando"\n'''
if reroute_anchor not in s:
    raise SystemExit('live reroute anchor not found')
s = s.replace(
    reroute_anchor,
    '''            val current = activeRoute\n            val accuracyAwareThreshold = max(OFF_ROUTE_METERS, if (location.hasAccuracy()) location.accuracy * 2.2f else OFF_ROUTE_METERS)\n            if (current != null && distanceToRoute(point, current.points) > accuracyAwareThreshold && SystemClock.elapsedRealtime() - lastRerouteAt > 22000L) recalculateFrom(point)\n            else status = "Navegando"\n''',
    1
)

# Landscape: keep all controls on-screen. In landscape the existing maneuver card already carries ETA,
# so hide the secondary trip bar and use a shorter map.
map_height_anchor = '''                                    immersiveMode -> 220.dp\n'''
if map_height_anchor not in s:
    raise SystemExit('v12.0.1 immersive height anchor not found')
s = s.replace(
    map_height_anchor,
    '''                                    isLandscape && immersiveMode -> 138.dp\n                                    isLandscape -> 170.dp\n                                    immersiveMode -> 220.dp\n''',
    1
)

trip_bar_anchor = '                if (immersiveMode) {\n                    Spacer(Modifier.height(5.dp))\n                    Surface(\n'
if trip_bar_anchor not in s:
    raise SystemExit('v12 trip bar anchor not found')
s = s.replace(
    trip_bar_anchor,
    '                if (immersiveMode && !isLandscape) {\n                    Spacer(Modifier.height(5.dp))\n                    Surface(\n',
    1
)

# Make the dock denser in landscape while keeping touch targets usable.
dock_padding_anchor = 'modifier = Modifier.fillMaxWidth().padding(horizontal = 7.dp, vertical = 7.dp),\n'
if dock_padding_anchor not in s:
    raise SystemExit('dock padding anchor not found')
s = s.replace(
    dock_padding_anchor,
    'modifier = Modifier.fillMaxWidth().padding(horizontal = if (isLandscape) 5.dp else 7.dp, vertical = if (isLandscape) 4.dp else 7.dp),\n',
    1
)

# Bottom sheet: quick Work + Stop controls.
quick_row_anchor = '''                                TextButton(onClick = {\n                                    toolsExpanded = false\n                                    if (prefs.contains(HOME_LAT)) {\n                                        selectDestination(SearchResult(LatLng(prefs.getLong(HOME_LAT, 0L).let(Double::fromBits), prefs.getLong(HOME_LON, 0L).let(Double::fromBits)), "Casa · Netheris"))\n                                    } else status = "Casa no guardada"\n                                }) { Text("CASA", color = Color.White, fontSize = 9.sp) }\n'''
if quick_row_anchor not in s:
    raise SystemExit('CASA quick button anchor not found')
work_button = quick_row_anchor + '''                                TextButton(onClick = {\n                                    toolsExpanded = false\n                                    if (prefs.contains(WORK_LAT) && prefs.contains(WORK_LON)) {\n                                        selectDestination(SearchResult(LatLng(prefs.getLong(WORK_LAT, 0L).let(Double::fromBits), prefs.getLong(WORK_LON, 0L).let(Double::fromBits)), "Trabajo · Netheris"))\n                                    } else status = "Trabajo no guardado"\n                                }) { Text("TRABAJO", color = Color(0xFF69F7C8), fontSize = 9.sp) }\n'''
s = s.replace(quick_row_anchor, work_button, 1)

# Add a dedicated stop row before favorites/history.
fav_anchor = '''                            if (favorites.isNotEmpty()) {\n'''
if fav_anchor not in s:
    raise SystemExit('favorites anchor not found')
stop_ui = '''                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {\n                                TextButton(onClick = {\n                                    toolsExpanded = false\n                                    if (destination == null) status = "Primero selecciona destino" else {\n                                        addingStop = true\n                                        searchPanelOpen = true\n                                        searchText = ""\n                                        status = "Busca una parada intermedia"\n                                    }\n                                }) { Text(if (waypoint == null) "+ PARADA" else "CAMBIAR PARADA", color = Color(0xFF66E7FF), fontSize = 9.sp) }\n                                if (waypoint != null) {\n                                    TextButton(onClick = {\n                                        waypoint = null\n                                        routeOptions = emptyList()\n                                        activeRoute = null\n                                        status = "Parada eliminada · recalcula la ruta"\n                                    }) { Text("QUITAR PARADA", color = Color(0xFFFFA9BC), fontSize = 9.sp) }\n                                }\n                            }\n                            waypoint?.let { stop ->\n                                Text("PARADA · ${stop.label}", color = Color(0xFF8DA7B9), fontSize = 8.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)\n                            }\n\n'''
s = s.replace(fav_anchor, stop_ui + fav_anchor, 1)

# Save current location as Work next to the existing Home action.
home_save_anchor = '''                            TextButton(\n                                onClick = {\n                                    val save: (LatLng) -> Unit = { p ->\n                                        prefs.edit().putLong(HOME_LAT, p.latitude.toBits()).putLong(HOME_LON, p.longitude.toBits()).apply()\n                                        showHome(p, false)\n                                        status = "Casa guardada"\n                                    }\n                                    lastLocation?.let(save) ?: requestLocation { it?.let(save) }\n                                },\n                                modifier = Modifier.fillMaxWidth()\n                            ) { Text("GUARDAR UBICACIÓN ACTUAL COMO CASA", color = Color(0xFF9EB6C8), fontSize = 9.sp) }\n'''
if home_save_anchor not in s:
    raise SystemExit('home save anchor not found')
work_save = home_save_anchor + '''                            TextButton(\n                                onClick = {\n                                    val saveWork: (LatLng) -> Unit = { p ->\n                                        prefs.edit().putLong(WORK_LAT, p.latitude.toBits()).putLong(WORK_LON, p.longitude.toBits()).apply()\n                                        status = "Trabajo guardado"\n                                    }\n                                    lastLocation?.let(saveWork) ?: requestLocation { it?.let(saveWork) }\n                                },\n                                modifier = Modifier.fillMaxWidth()\n                            ) { Text("GUARDAR UBICACIÓN ACTUAL COMO TRABAJO", color = Color(0xFF69F7C8), fontSize = 9.sp) }\n'''
s = s.replace(home_save_anchor, work_save, 1)

# Reset waypoint when the user explicitly starts a completely new route.
new_route_anchor = '''                                    destination = null\n                                    searchText = ""\n                                    status = "Katherine lista · busca un nuevo destino"\n'''
if new_route_anchor in s:
    s = s.replace(
        new_route_anchor,
        '''                                    destination = null\n                                    waypoint = null\n                                    addingStop = false\n                                    searchText = ""\n                                    status = "Katherine lista · busca un nuevo destino"\n''',
        1
    )

# Version strings.
s = s.replace('NetherisGPS/12.0.1 Android', 'NetherisGPS/13.0 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text().replace('NETHERIS NAVIGATION AI · V12.0.1', 'NETHERIS NAVIGATION AI · V13.0')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 121', 'versionCode = 130').replace('versionName = "12.0.1"', 'versionName = "13.0.0"')
build.write_text(b)

print('Applied Netheris GPS v13 landscape + intelligent navigation')
