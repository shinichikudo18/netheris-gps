from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# Add a local broadcast action shared by shell + phone navigation.
anchor = 'private const val ACTION_SMART_START_NAV = "cl.netheris.gps.SMART_START_NAV"\n'
if anchor not in s:
    raise SystemExit('smart start constant not found')
s = s.replace(anchor, anchor + 'private const val ACTION_SMART_STOP_NAV = "cl.netheris.gps.SMART_STOP_NAV"\n')

# Add a full UI/session reset after the existing stopNavigation helper.
old_stop = '''    fun stopNavigation() {\n        trackingListener?.let { try { locationManager.removeUpdates(it) } catch (_: Exception) {} }\n        trackingListener = null\n        demoRunnable?.let { mainHandler.removeCallbacks(it) }\n        demoRunnable = null\n        navigationActive = false\n        demoActive = false\n        status = "Navegación detenida"\n    }\n'''
new_stop = '''    fun stopNavigation() {\n        trackingListener?.let { try { locationManager.removeUpdates(it) } catch (_: Exception) {} }\n        trackingListener = null\n        demoRunnable?.let { mainHandler.removeCallbacks(it) }\n        demoRunnable = null\n        navigationActive = false\n        demoActive = false\n        runCatching {\n            context.startService(\n                Intent(context, NavigationForegroundService::class.java)\n                    .setAction(NavigationForegroundService.ACTION_STOP)\n            )\n        }\n        status = "Navegación detenida"\n    }\n\n    fun resetToExploration() {\n        stopNavigation()\n        toolsExpanded = false\n        routePolyline?.let { map?.removePolyline(it) }\n        routePolyline = null\n        activeRoute = null\n        routeOptions = emptyList()\n        selectedRouteIndex = 0\n        nextInstruction = ""\n        nextDistance = ""\n        remainingInfo = ""\n        speedInfo = "0 km/h"\n        etaInfo = "--:--"\n        currentStepIndex = 0\n        lastSpokenFarStep = -1\n        lastSpokenNearStep = -1\n        searchResults = emptyList()\n        status = "Katherine lista · busca un nuevo destino"\n    }\n'''
if old_stop not in s:
    raise SystemExit('stopNavigation anchor not found')
s = s.replace(old_stop, new_stop)

# Receiver handles both one-touch start and unified stop from shell.
old_receiver = '''            override fun onReceive(receiverContext: Context?, intent: Intent?) {\n                if (intent?.action != ACTION_SMART_START_NAV) return\n                val lat = intent.getDoubleExtra(EXTRA_SMART_LAT, Double.NaN)\n                val lon = intent.getDoubleExtra(EXTRA_SMART_LON, Double.NaN)\n                if (lat.isNaN() || lon.isNaN()) {\n                    status = "Destino inválido"\n                    return\n                }\n                val label = intent.getStringExtra(EXTRA_SMART_LABEL)?.takeIf { it.isNotBlank() } ?: "Destino"\n                mainHandler.post {\n                    selectDestination(SearchResult(LatLng(lat, lon), label), false)\n                    startNavigation()\n                }\n            }\n'''
new_receiver = '''            override fun onReceive(receiverContext: Context?, intent: Intent?) {\n                when (intent?.action) {\n                    ACTION_SMART_STOP_NAV -> {\n                        mainHandler.post { resetToExploration() }\n                    }\n                    ACTION_SMART_START_NAV -> {\n                        val lat = intent.getDoubleExtra(EXTRA_SMART_LAT, Double.NaN)\n                        val lon = intent.getDoubleExtra(EXTRA_SMART_LON, Double.NaN)\n                        if (lat.isNaN() || lon.isNaN()) {\n                            status = "Destino inválido"\n                            return\n                        }\n                        val label = intent.getStringExtra(EXTRA_SMART_LABEL)?.takeIf { it.isNotBlank() } ?: "Destino"\n                        mainHandler.post {\n                            selectDestination(SearchResult(LatLng(lat, lon), label), false)\n                            startNavigation()\n                        }\n                    }\n                }\n            }\n'''
if old_receiver not in s:
    raise SystemExit('receiver anchor not found')
s = s.replace(old_receiver, new_receiver)

# Receiver filter must listen for stop as well.
old_filter = '''            IntentFilter(ACTION_SMART_START_NAV),\n            ContextCompat.RECEIVER_NOT_EXPORTED\n'''
new_filter = '''            IntentFilter().apply {\n                addAction(ACTION_SMART_START_NAV)\n                addAction(ACTION_SMART_STOP_NAV)\n            },\n            ContextCompat.RECEIVER_NOT_EXPORTED\n'''
if old_filter not in s:
    raise SystemExit('receiver filter anchor not found')
s = s.replace(old_filter, new_filter)

# Bottom DETENER should fully return to exploration instead of leaving the route UI behind.
s = s.replace(
    'onClick = { if (navigationActive && !demoActive) stopNavigation() else startNavigation() },',
    'onClick = { if (navigationActive && !demoActive) resetToExploration() else startNavigation() },'
)

# Natural arrival also leaves a clean screen ready for a new trip.
s = s.replace(
    'speak("Llegaste al destino"); stopNavigation(); toolsExpanded = false; status = "Destino alcanzado · listo para nueva ruta"',
    'speak("Llegaste al destino"); resetToExploration(); status = "Destino alcanzado · listo para nueva ruta"'
)

s = s.replace('NetherisGPS/8.2 Android', 'NetherisGPS/8.2.1 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text()
old_shell_stop = '''    fun stopBackground() {\n        context.startService(Intent(context, NavigationForegroundService::class.java).setAction(NavigationForegroundService.ACTION_STOP))\n    }\n'''
new_shell_stop = '''    fun stopBackground() {\n        runCatching {\n            context.startService(Intent(context, NavigationForegroundService::class.java).setAction(NavigationForegroundService.ACTION_STOP))\n        }\n        context.sendBroadcast(\n            Intent("cl.netheris.gps.SMART_STOP_NAV").setPackage(context.packageName)\n        )\n    }\n'''
if old_shell_stop not in t:
    raise SystemExit('shell stopBackground anchor not found')
t = t.replace(old_shell_stop, new_shell_stop)
t = t.replace('NETHERIS NAVIGATION AI · V8.2', 'NETHERIS NAVIGATION AI · V8.2.1')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 83', 'versionCode = 84').replace('versionName = "8.2.0"', 'versionName = "8.2.1"')
build.write_text(b)

print('Applied Netheris GPS v8.2.1 unified stop + exploration reset')
