from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# Storage keys.
s = s.replace('private const val RECENTS_JSON = "recents_json"\n', 'private const val RECENTS_JSON = "recents_json"\nprivate const val FAVORITES_JSON = "favorites_json"\nprivate const val TRIP_HISTORY_JSON = "trip_history_json"\n')

# Generic list persistence helpers for favorites/history.
anchor = '''private fun loadRecents(prefs: android.content.SharedPreferences): List<SearchResult> {\n    return try {\n        val array = JSONArray(prefs.getString(RECENTS_JSON, "[]") ?: "[]")\n        List(array.length()) { i ->\n            val o = array.getJSONObject(i)\n            SearchResult(LatLng(o.getDouble("lat"), o.getDouble("lon")), o.getString("label"))\n        }\n    } catch (_: Exception) { emptyList() }\n}\n'''
if anchor not in s:
    raise SystemExit('loadRecents anchor not found')
helpers = anchor + '''\nprivate fun loadPlaces(prefs: android.content.SharedPreferences, key: String): List<SearchResult> {\n    return try {\n        val array = JSONArray(prefs.getString(key, "[]") ?: "[]")\n        List(array.length()) { i ->\n            val o = array.getJSONObject(i)\n            SearchResult(LatLng(o.getDouble("lat"), o.getDouble("lon")), o.getString("label"))\n        }\n    } catch (_: Exception) { emptyList() }\n}\n\nprivate fun savePlaceList(\n    prefs: android.content.SharedPreferences,\n    key: String,\n    result: SearchResult,\n    maxItems: Int\n): List<SearchResult> {\n    val items = loadPlaces(prefs, key).filterNot {\n        distanceMeters(it.point, result.point) < 25f || it.label == result.label\n    }.toMutableList()\n    items.add(0, result)\n    val array = JSONArray()\n    items.take(maxItems).forEach {\n        array.put(JSONObject().put("label", it.label).put("lat", it.point.latitude).put("lon", it.point.longitude))\n    }\n    prefs.edit().putString(key, array.toString()).apply()\n    return items.take(maxItems)\n}\n'''
s = s.replace(anchor, helpers)

# State lists.
state_anchor = '    var recents by remember { mutableStateOf(loadRecents(prefs)) }\n'
if state_anchor not in s:
    raise SystemExit('recents state anchor not found')
s = s.replace(state_anchor, state_anchor + '    var favorites by remember { mutableStateOf(loadPlaces(prefs, FAVORITES_JSON)) }\n    var tripHistory by remember { mutableStateOf(loadPlaces(prefs, TRIP_HISTORY_JSON)) }\n')

# Add helpers inside composable before speak().
speak_anchor = '    fun speak(text: String) {\n'
if speak_anchor not in s:
    raise SystemExit('speak anchor not found')
local_helpers = '''    fun addFavorite(result: SearchResult) {\n        favorites = savePlaceList(prefs, FAVORITES_JSON, result, 8)\n        // Keep legacy single favorite compatible with old UI/markers.\n        prefs.edit()\n            .putLong(FAVORITE_LAT, result.point.latitude.toBits())\n            .putLong(FAVORITE_LON, result.point.longitude.toBits())\n            .putString(FAVORITE_LABEL, result.label.substringBefore(","))\n            .apply()\n        showFavorite(result.point, result.label.substringBefore(","), false)\n        status = "Favorito guardado"\n    }\n\n    fun recordTrip(result: SearchResult) {\n        tripHistory = savePlaceList(prefs, TRIP_HISTORY_JSON, result, 12)\n    }\n\n'''
s = s.replace(speak_anchor, local_helpers + speak_anchor)

# Record natural arrivals before reset.
s = s.replace(
    'remainingInfo = "0 m"; nextInstruction = "Llegaste al destino 🎉"; nextDistance = ""; speak("Llegaste al destino"); resetToExploration(); status = "Destino alcanzado · listo para nueva ruta"',
    'remainingInfo = "0 m"; nextInstruction = "Llegaste al destino 🎉"; nextDistance = ""; destination?.let { recordTrip(it) }; speak("Llegaste al destino"); resetToExploration(); status = "Destino alcanzado · listo para nueva ruta"'
)

# Route preview summary in v8 UI, only before navigating.
preview_anchor = '''                if (!immersiveMode) {\n                    Spacer(Modifier.height(6.dp))\n                    Surface(\n'''
if preview_anchor not in s:
    raise SystemExit('v8 non immersive anchor not found')
preview = '''                if (!immersiveMode && activeRoute != null) {\n                    val previewRoute = activeRoute!!\n                    val previewMinutes = (previewRoute.durationSeconds / 60.0).toInt().coerceAtLeast(1)\n                    Spacer(Modifier.height(5.dp))\n                    Surface(\n                        modifier = Modifier.fillMaxWidth(),\n                        shape = RoundedCornerShape(16.dp),\n                        color = Color(0xFF0A1B28)\n                    ) {\n                        Row(\n                            modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),\n                            horizontalArrangement = Arrangement.SpaceBetween\n                        ) {\n                            Column {\n                                Text("RUTA PREPARADA", color = Color(0xFF5FE7FF), fontSize = 9.sp, fontWeight = FontWeight.Black)\n                                Text(destination?.label?.substringBefore(",") ?: "Destino", color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Bold)\n                            }\n                            Column {\n                                Text(formatDistance(previewRoute.distanceMeters.toFloat()), color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Bold)\n                                Text("~$previewMinutes min", color = Color(0xFFA6C0D2), fontSize = 10.sp)\n                            }\n                        }\n                    }\n                }\n\n'''
s = s.replace(preview_anchor, preview + preview_anchor)

# Replace the old single favorite save action with multi-favorite helper.
old_fav_save = '''                                TextButton(onClick = {\n                                    val d = destination ?: run { status = "Selecciona destino"; return@TextButton }\n                                    prefs.edit().putLong(FAVORITE_LAT, d.point.latitude.toBits()).putLong(FAVORITE_LON, d.point.longitude.toBits()).putString(FAVORITE_LABEL, d.label.substringBefore(",")).apply()\n                                    showFavorite(d.point, d.label.substringBefore(","), false); status = "Favorito guardado"\n                                }) { Text("★ GUARDAR", color = Color(0xFFFFD76A), fontSize = 10.sp) }\n'''
new_fav_save = '''                                TextButton(onClick = {\n                                    val d = destination ?: run { status = "Selecciona destino"; return@TextButton }\n                                    addFavorite(d)\n                                }) { Text("★ GUARDAR", color = Color(0xFFFFD76A), fontSize = 10.sp) }\n'''
if old_fav_save in s:
    s = s.replace(old_fav_save, new_fav_save)

# Add Trip Center rows inside tools before the final save-home row.
tools_anchor = '''                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {\n                                TextButton(onClick = {\n                                    val save: (LatLng) -> Unit = { p -> prefs.edit().putLong(HOME_LAT, p.latitude.toBits()).putLong(HOME_LON, p.longitude.toBits()).apply(); showHome(p, false); status = "Casa guardada" }\n'''
if tools_anchor not in s:
    raise SystemExit('tools final row anchor not found')
trip_center = '''                            if (favorites.isNotEmpty()) {\n                                Text("FAVORITOS", color = Color(0xFFFFD76A), fontSize = 8.sp, fontWeight = FontWeight.Black, modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp))\n                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(2.dp)) {\n                                    favorites.take(3).forEach { fav ->\n                                        TextButton(onClick = { toolsExpanded = false; selectDestination(fav) }) {\n                                            Text("★ ${fav.label.substringBefore(",").take(14)}", color = Color(0xFFFFE39A), fontSize = 8.sp, maxLines = 1)\n                                        }\n                                    }\n                                }\n                            }\n                            if (tripHistory.isNotEmpty()) {\n                                Text("ÚLTIMOS VIAJES", color = Color(0xFF6FE7FF), fontSize = 8.sp, fontWeight = FontWeight.Black, modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp))\n                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(2.dp)) {\n                                    tripHistory.take(3).forEach { trip ->\n                                        TextButton(onClick = { toolsExpanded = false; selectDestination(trip) }) {\n                                            Text("↺ ${trip.label.substringBefore(",").take(14)}", color = Color(0xFFA6C0D2), fontSize = 8.sp, maxLines = 1)\n                                        }\n                                    }\n                                }\n                            }\n'''
s = s.replace(tools_anchor, trip_center + tools_anchor)

s = s.replace('NetherisGPS/8.2.2 Android', 'NetherisGPS/9.0 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text().replace('NETHERIS NAVIGATION AI · V8.2.2', 'NETHERIS NAVIGATION AI · V9.0')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 85', 'versionCode = 90').replace('versionName = "8.2.2"', 'versionName = "9.0.0"')
build.write_text(b)

print('Applied Netheris GPS v9 Trip Center + multi favorites + route preview')
