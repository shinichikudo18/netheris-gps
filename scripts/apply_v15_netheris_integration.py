from pathlib import Path

# --- Navigation service -> NetherisBridge events ---
service = Path('app/src/main/java/cl/netheris/gps/nav/NavigationForegroundService.kt')
s = service.read_text()

if 'import cl.netheris.gps.bridge.NetherisBridge\n' not in s:
    s = s.replace('import cl.netheris.gps.R\n', 'import cl.netheris.gps.R\nimport cl.netheris.gps.bridge.NetherisBridge\n')

field_anchor = '    private var lastReroute = 0L\n'
if field_anchor not in s:
    raise SystemExit('v15 service field anchor not found')
s = s.replace(field_anchor, field_anchor + '''    private var lastBridgeUpdateAt = 0L\n    private val sentHomeThresholds = mutableSetOf<Int>()\n''', 1)

start_anchor = '''        NavStateStore.setDestination(this, destinationLabel, lat, lon)\n        NavStateStore.setActive(this, true)\n        startForeground(NOTIFICATION_ID, buildNotification("Preparando ruta…", destinationLabel))\n'''
if start_anchor not in s:
    raise SystemExit('v15 startSession anchor not found')
s = s.replace(start_anchor, '''        NavStateStore.setDestination(this, destinationLabel, lat, lon)\n        NavStateStore.setActive(this, true)\n        sentHomeThresholds.clear()\n        lastBridgeUpdateAt = 0L\n        NetherisBridge.emit(\n            this,\n            "navigation_started",\n            JSONObject()\n                .put("active", true)\n                .put("destination", destinationLabel)\n                .put("destination_lat", lat)\n                .put("destination_lon", lon)\n        )\n        startForeground(NOTIFICATION_ID, buildNotification("Preparando ruta…", destinationLabel))\n''', 1)

update_anchor = '''        NavStateStore.update(this, instruction, next, formatDistance(remaining), eta, "${max(0, speed.toInt())} km/h")\n        updateNotification(if (next.isBlank()) instruction else "$instruction · $next", "$destinationLabel · ${formatDistance(remaining)} · ETA $eta")\n'''
if update_anchor not in s:
    raise SystemExit('v15 update anchor not found')
s = s.replace(update_anchor, '''        val speedText = "${max(0, speed.toInt())} km/h"\n        val remainingText = formatDistance(remaining)\n        NavStateStore.update(this, instruction, next, remainingText, eta, speedText)\n        updateNotification(if (next.isBlank()) instruction else "$instruction · $next", "$destinationLabel · $remainingText · ETA $eta")\n\n        val bridgeNow = SystemClock.elapsedRealtime()\n        if (bridgeNow - lastBridgeUpdateAt >= 15000L) {\n            lastBridgeUpdateAt = bridgeNow\n            NetherisBridge.emit(\n                this,\n                "navigation_updated",\n                JSONObject()\n                    .put("active", true)\n                    .put("destination", destinationLabel)\n                    .put("instruction", instruction)\n                    .put("next_distance", next)\n                    .put("remaining", remainingText)\n                    .put("remaining_meters", remaining.toInt())\n                    .put("eta", eta)\n                    .put("speed_kmh", max(0, speed.toInt())),\n                here.lat,\n                here.lon\n            )\n            emitHomeApproach(here, remainingText, eta)\n        }\n''', 1)

arrival_anchor = '''        if (distance(here, dest) < 35f) {\n            NavStateStore.update(this, "Llegaste al destino", "", "0 m", eta, "0 km/h")\n            updateNotification("Llegaste al destino", destinationLabel)\n            stopNavigation(clearState = false)\n'''
if arrival_anchor not in s:
    raise SystemExit('v15 arrival anchor not found')
s = s.replace(arrival_anchor, '''        if (distance(here, dest) < 35f) {\n            NavStateStore.update(this, "Llegaste al destino", "", "0 m", eta, "0 km/h")\n            updateNotification("Llegaste al destino", destinationLabel)\n            NetherisBridge.emit(\n                this,\n                "arrived",\n                JSONObject()\n                    .put("active", false)\n                    .put("destination", destinationLabel)\n                    .put("eta", eta),\n                here.lat,\n                here.lon\n            )\n            stopNavigation(clearState = false)\n''', 1)

stop_anchor = '''    private fun stopNavigation(clearState: Boolean = true) {\n        listener?.let { runCatching { locationManager.removeUpdates(it) } }\n        listener = null\n        route = null\n        if (clearState) NavStateStore.setActive(this, false)\n'''
if stop_anchor not in s:
    raise SystemExit('v15 stop anchor not found')
s = s.replace(stop_anchor, '''    private fun stopNavigation(clearState: Boolean = true) {\n        listener?.let { runCatching { locationManager.removeUpdates(it) } }\n        listener = null\n        route = null\n        if (clearState) {\n            NavStateStore.setActive(this, false)\n            NetherisBridge.emit(\n                this,\n                "navigation_stopped",\n                JSONObject().put("active", false).put("destination", destinationLabel)\n            )\n        }\n''', 1)

helper_anchor = '    private fun calculateRoute(origin: P, dest: P) {\n'
if helper_anchor not in s:
    raise SystemExit('v15 helper anchor not found')
helper = '''    private fun emitHomeApproach(here: P, remainingText: String, eta: String) {\n        val prefs = getSharedPreferences("netheris_gps", MODE_PRIVATE)\n        if (!prefs.contains("home_lat") || !prefs.contains("home_lon")) return\n        val homeLat = prefs.getLong("home_lat", 0L).let(Double::fromBits)\n        val homeLon = prefs.getLong("home_lon", 0L).let(Double::fromBits)\n        val meters = NetherisBridge.distanceMeters(here.lat, here.lon, homeLat, homeLon)\n        val thresholds = listOf(5000, 2000, 500)\n        for (threshold in thresholds) {\n            if (meters <= threshold && threshold !in sentHomeThresholds) {\n                sentHomeThresholds += threshold\n                NetherisBridge.emit(\n                    this,\n                    "approaching_home",\n                    JSONObject()\n                        .put("active", true)\n                        .put("destination", destinationLabel)\n                        .put("home_distance_meters", meters.toInt())\n                        .put("threshold_meters", threshold)\n                        .put("remaining", remainingText)\n                        .put("eta", eta),\n                    here.lat,\n                    here.lon\n                )\n            }\n        }\n    }\n\n'''
s = s.replace(helper_anchor, helper + helper_anchor, 1)
service.write_text(s)

# --- Deep-link command entry point ---
manifest = Path('app/src/main/AndroidManifest.xml')
m = manifest.read_text()
command_entry = '''        <activity\n            android:name=".bridge.NetherisCommandActivity"\n            android:exported="true">\n            <intent-filter>\n                <action android:name="android.intent.action.VIEW" />\n                <category android:name="android.intent.category.DEFAULT" />\n                <category android:name="android.intent.category.BROWSABLE" />\n                <data android:scheme="netheris" />\n            </intent-filter>\n        </activity>\n\n'''
if '.bridge.NetherisCommandActivity' not in m:
    marker = '        <activity\n            android:name=".MainActivity"\n            android:exported="false" />\n\n'
    if marker not in m:
        raise SystemExit('v15 manifest activity anchor not found')
    m = m.replace(marker, marker + command_entry, 1)
manifest.write_text(m)

# --- Version ---
main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
t = main.read_text().replace('NetherisGPS/14.0 Android', 'NetherisGPS/15.0 Android')
main.write_text(t)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
u = shell.read_text().replace('NETHERIS NAVIGATION AI · V14.0', 'NETHERIS NAVIGATION AI · V15.0')
shell.write_text(u)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 140', 'versionCode = 150').replace('versionName = "14.0.0"', 'versionName = "15.0.0"')
build.write_text(b)

print('Applied Netheris GPS v15 integration core')
