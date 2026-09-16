from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# Global search: stop forcing Chile so Netheris GPS works naturally while travelling.
old_search = '''private fun searchPlaces(query: String): List<SearchResult> {\n    val encoded = URLEncoder.encode("$query, Chile", StandardCharsets.UTF_8.toString())\n    val url = "https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&countrycodes=cl&q=$encoded"\n    val items = JSONArray(httpGet(url))\n'''
new_search = '''private fun searchPlaces(query: String): List<SearchResult> {\n    val clean = query.trim()\n    if (clean.isBlank()) return emptyList()\n    val encoded = URLEncoder.encode(clean, StandardCharsets.UTF_8.toString())\n    val url = "https://nominatim.openstreetmap.org/search?format=jsonv2&limit=7&addressdetails=1&dedupe=1&accept-language=es&q=$encoded"\n    val items = JSONArray(httpGet(url))\n'''
if old_search not in s:
    raise SystemExit('global search anchor not found')
s = s.replace(old_search, new_search, 1)

# Network resilience: retry once for transient mobile-data failures before surfacing an error.
old_http = '''private fun httpGet(url: String): String {\n    val connection = URL(url).openConnection() as HttpURLConnection\n    return try {\n        connection.requestMethod = "GET"\n        connection.connectTimeout = 10000\n        connection.readTimeout = 15000\n        connection.setRequestProperty("User-Agent", "NetherisGPS/1.8 Android")\n        connection.setRequestProperty("Accept", "application/json")\n        val code = connection.responseCode\n        if (code !in 200..299) throw IllegalStateException("HTTP $code")\n        connection.inputStream.bufferedReader().use { it.readText() }\n    } finally {\n        connection.disconnect()\n    }\n}\n'''
new_http = '''private fun httpGet(url: String): String {\n    var lastError: Exception? = null\n    repeat(2) { attempt ->\n        val connection = URL(url).openConnection() as HttpURLConnection\n        try {\n            connection.requestMethod = "GET"\n            connection.connectTimeout = 10000\n            connection.readTimeout = 15000\n            connection.setRequestProperty("User-Agent", "NetherisGPS/14.0 Android")\n            connection.setRequestProperty("Accept", "application/json")\n            connection.setRequestProperty("Accept-Language", "es")\n            val code = connection.responseCode\n            if (code !in 200..299) throw IllegalStateException("HTTP $code")\n            return connection.inputStream.bufferedReader().use { it.readText() }\n        } catch (e: Exception) {\n            lastError = e\n            if (attempt == 0) Thread.sleep(450L)\n        } finally {\n            connection.disconnect()\n        }\n    }\n    throw lastError ?: IllegalStateException("Error de red")\n}\n'''
if old_http not in s:
    raise SystemExit('httpGet anchor not found')
s = s.replace(old_http, new_http, 1)

# Keep a longer travel history without changing the existing JSON format.
s = s.replace('existing.take(4).forEach {', 'existing.take(8).forEach {', 1)

# Use Spanish TTS adapted to the device region when available.
old_tts = '        tts.language = Locale("es", "CL")\n'
new_tts = '''        val region = Locale.getDefault().country.takeIf { it.isNotBlank() } ?: "CL"\n        val preferred = Locale("es", region)\n        tts.language = if (tts.isLanguageAvailable(preferred) >= TextToSpeech.LANG_AVAILABLE) preferred else Locale("es")\n'''
if old_tts not in s:
    raise SystemExit('TTS locale anchor not found')
s = s.replace(old_tts, new_tts, 1)

# Travel-friendly version/User-Agent strings created by later patches.
s = s.replace('NetherisGPS/13.1.1 Android', 'NetherisGPS/14.0 Android')
s = s.replace('NetherisGPS/13.1 Android', 'NetherisGPS/14.0 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text()
t = t.replace('NETHERIS NAVIGATION AI · V13.1.1', 'NETHERIS NAVIGATION AI · V14.0')
t = t.replace('NETHERIS NAVIGATION AI · V13.1', 'NETHERIS NAVIGATION AI · V14.0')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text()
b = b.replace('versionCode = 133', 'versionCode = 140')
b = b.replace('versionCode = 132', 'versionCode = 140')
b = b.replace('versionName = "13.1.1"', 'versionName = "14.0.0"')
b = b.replace('versionName = "13.1.0"', 'versionName = "14.0.0"')
build.write_text(b)

print('Applied Netheris GPS v14 Travel Mode')
