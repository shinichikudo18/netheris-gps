from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# Move toolsExpanded into the main state block so navigation/search helpers can reset it.
state_anchor = '    var demoRunnable by remember { mutableStateOf<Runnable?>(null) }\n'
if state_anchor not in s:
    raise SystemExit('state anchor not found')
s = s.replace(state_anchor, state_anchor + '    var toolsExpanded by remember { mutableStateOf(false) }\n')
s = s.replace('    var toolsExpanded by remember { mutableStateOf(false) }\n\n    val immersiveMode', '    val immersiveMode')

# Faster primary-route request for one-touch navigation. Alternatives remain available through manual RUTA/ALT.
fetch_anchor = '''private fun fetchRoutes(origin: LatLng, destination: LatLng): List<RouteResult> {\n    val url = "https://router.project-osrm.org/route/v1/driving/" +\n        "${origin.longitude},${origin.latitude};${destination.longitude},${destination.latitude}" +\n        "?overview=full&geometries=geojson&steps=true&alternatives=2"\n    val root = JSONObject(httpGet(url))\n    if (root.optString("code") != "Ok") return emptyList()\n    val routes = root.optJSONArray("routes") ?: return emptyList()\n    val result = mutableListOf<RouteResult>()\n    for (i in 0 until routes.length()) result.add(parseRoute(routes.getJSONObject(i)))\n    return result\n}\n'''
if fetch_anchor not in s:
    raise SystemExit('fetchRoutes anchor not found')
fast_func = fetch_anchor + '''\nprivate fun fetchPrimaryRoute(origin: LatLng, destination: LatLng): RouteResult? {\n    val url = "https://router.project-osrm.org/route/v1/driving/" +\n        "${origin.longitude},${origin.latitude};${destination.longitude},${destination.latitude}" +\n        "?overview=full&geometries=geojson&steps=true&alternatives=false"\n    val root = JSONObject(httpGet(url))\n    if (root.optString("code") != "Ok") return null\n    val route = root.optJSONArray("routes")?.optJSONObject(0) ?: return null\n    return parseRoute(route)\n}\n'''
s = s.replace(fetch_anchor, fast_func)

# Fresh destination selection = fresh UI/session.
old_select = '''        destination = result\n        searchResults = emptyList()\n        routeOptions = emptyList()\n        activeRoute = null\n        selectedRouteIndex = 0\n'''
new_select = '''        toolsExpanded = false\n        destination = result\n        searchResults = emptyList()\n        routeOptions = emptyList()\n        activeRoute = null\n        routePolyline?.let { readyMap.removePolyline(it) }\n        routePolyline = null\n        nextInstruction = ""\n        nextDistance = ""\n        remainingInfo = ""\n        speedInfo = "0 km/h"\n        etaInfo = "--:--"\n        selectedRouteIndex = 0\n'''
if old_select not in s:
    raise SystemExit('select destination anchor not found')
s = s.replace(old_select, new_select)

# Search resets secondary tools and stale route presentation, but keeps current destination until a result is picked.
old_find = '''    fun findDestination() {\n        val query = searchText.trim()\n        if (query.isEmpty()) { status = "Escribe un destino"; return }\n        status = "Buscando…"\n'''
new_find = '''    fun findDestination() {\n        val query = searchText.trim()\n        if (query.isEmpty()) { status = "Escribe un destino"; return }\n        if (!navigationActive && !demoActive) {\n            toolsExpanded = false\n            routePolyline?.let { map?.removePolyline(it) }\n            routePolyline = null\n            activeRoute = null\n            routeOptions = emptyList()\n            nextInstruction = ""\n            nextDistance = ""\n            remainingInfo = ""\n            speedInfo = "0 km/h"\n            etaInfo = "--:--"\n        }\n        status = "Buscando…"\n'''
if old_find not in s:
    raise SystemExit('findDestination anchor not found')
s = s.replace(old_find, new_find)

# Smart start: fetch only primary route, avoiding alternatives during initial launch.
old_prepare = '''                        val routes = fetchRoutes(origin, dest.point)\n                        mainHandler.post {\n                            if (routes.isEmpty()) {\n                                status = "No pude calcular ruta"\n                            } else {\n                                routeOptions = routes\n                                selectedRouteIndex = 0\n                                drawRoute(routes[0], origin, dest.point)\n                                status = "Ruta lista · iniciando navegación…"\n                                startNavigation()\n                            }\n                        }\n'''
new_prepare = '''                        val primary = fetchPrimaryRoute(origin, dest.point)\n                        mainHandler.post {\n                            if (primary == null) {\n                                status = "No pude calcular ruta"\n                            } else {\n                                routeOptions = listOf(primary)\n                                selectedRouteIndex = 0\n                                drawRoute(primary, origin, dest.point)\n                                status = "Ruta lista · iniciando navegación…"\n                                startNavigation()\n                            }\n                        }\n'''
if old_prepare not in s:
    raise SystemExit('smart prepare anchor not found')
s = s.replace(old_prepare, new_prepare)

# Clean arrival state enough to immediately start another search.
old_arrival = '''                remainingInfo = "0 m"; nextInstruction = "Llegaste al destino 🎉"; nextDistance = ""; speak("Llegaste al destino"); stopNavigation(); status = "Destino alcanzado"\n'''
new_arrival = '''                remainingInfo = "0 m"; nextInstruction = "Llegaste al destino 🎉"; nextDistance = ""; speak("Llegaste al destino"); stopNavigation(); toolsExpanded = false; status = "Destino alcanzado · listo para nueva ruta"\n'''
s = s.replace(old_arrival, new_arrival)

# Clean demo completion too.
s = s.replace('demoActive = false; navigationActive = false; status = "DEMO finalizada"', 'demoActive = false; navigationActive = false; toolsExpanded = false; status = "DEMO finalizada · listo para nueva ruta"')

s = s.replace('NetherisGPS/8.1 Android', 'NetherisGPS/8.2 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text().replace('NETHERIS NAVIGATION AI · V8.1', 'NETHERIS NAVIGATION AI · V8.2')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 82', 'versionCode = 83').replace('versionName = "8.1.0"', 'versionName = "8.2.0"')
build.write_text(b)

print('Applied Netheris GPS v8.2 faster smart-start and clean new-route state')
