from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

s = s.replace(
    'import android.content.Context\n',
    'import android.content.BroadcastReceiver\nimport android.content.Context\nimport android.content.Intent\nimport android.content.IntentFilter\n'
)
s = s.replace(
    'import androidx.core.content.ContextCompat\n',
    'import androidx.core.content.ContextCompat\nimport cl.netheris.gps.nav.NavigationForegroundService\n'
)

const_anchor = 'private const val OFF_ROUTE_METERS = 90f\n'
if const_anchor not in s:
    raise SystemExit('MainActivity constants anchor not found')
s = s.replace(
    const_anchor,
    const_anchor + 'private const val ACTION_SMART_START_NAV = "cl.netheris.gps.SMART_START_NAV"\nprivate const val EXTRA_SMART_LAT = "smart_lat"\nprivate const val EXTRA_SMART_LON = "smart_lon"\nprivate const val EXTRA_SMART_LABEL = "smart_label"\n'
)

old_start = '''    fun startNavigation() {\n        val dest = destination ?: run { status = "Selecciona destino"; return }\n        val route = activeRoute ?: run { status = "Calcula una ruta"; return }\n        val hasPermission = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED\n        if (!hasPermission) { status = "Necesito permiso GPS"; return }\n        stopNavigation(); navigationActive = true; status = "Navegando"; speak("Navegación iniciada")\n        val listener = LocationListener { location ->\n'''
new_start = '''    fun startNavigation() {\n        val dest = destination ?: run { status = "Selecciona destino"; return }\n        val hasPermission = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED\n        if (!hasPermission) { status = "Necesito permiso GPS"; return }\n\n        if (activeRoute == null) {\n            fun prepare(origin: LatLng) {\n                status = "Katherine preparando navegación…"\n                Thread {\n                    try {\n                        val routes = fetchRoutes(origin, dest.point)\n                        mainHandler.post {\n                            if (routes.isEmpty()) {\n                                status = "No pude calcular ruta"\n                            } else {\n                                routeOptions = routes\n                                selectedRouteIndex = 0\n                                drawRoute(routes[0], origin, dest.point)\n                                status = "Ruta lista · iniciando navegación…"\n                                startNavigation()\n                            }\n                        }\n                    } catch (_: Exception) {\n                        mainHandler.post { status = "Error preparando navegación" }\n                    }\n                }.start()\n            }\n            lastLocation?.let(::prepare) ?: requestLocation { point ->\n                if (point != null) prepare(point) else status = "No pude obtener ubicación"\n            }\n            return\n        }\n\n        stopNavigation(); navigationActive = true; status = "Navegando"; speak("Navegación iniciada")\n\n        runCatching {\n            val bgIntent = Intent(context, NavigationForegroundService::class.java)\n                .setAction(NavigationForegroundService.ACTION_START)\n                .putExtra(NavigationForegroundService.EXTRA_LABEL, dest.label)\n                .putExtra(NavigationForegroundService.EXTRA_LAT, dest.point.latitude)\n                .putExtra(NavigationForegroundService.EXTRA_LON, dest.point.longitude)\n            ContextCompat.startForegroundService(context, bgIntent)\n        }\n\n        val listener = LocationListener { location ->\n'''
if old_start not in s:
    raise SystemExit('startNavigation anchor not found')
s = s.replace(old_start, new_start)

old_effect = '''    DisposableEffect(Unit) {\n        onDispose {\n            trackingListener?.let { try { locationManager.removeUpdates(it) } catch (_: Exception) {} }\n            demoRunnable?.let { mainHandler.removeCallbacks(it) }\n            tts.stop(); tts.shutdown()\n        }\n    }\n'''
new_effect = '''    DisposableEffect(context) {\n        val receiver = object : BroadcastReceiver() {\n            override fun onReceive(receiverContext: Context?, intent: Intent?) {\n                if (intent?.action != ACTION_SMART_START_NAV) return\n                val lat = intent.getDoubleExtra(EXTRA_SMART_LAT, Double.NaN)\n                val lon = intent.getDoubleExtra(EXTRA_SMART_LON, Double.NaN)\n                if (lat.isNaN() || lon.isNaN()) {\n                    status = "Destino inválido"\n                    return\n                }\n                val label = intent.getStringExtra(EXTRA_SMART_LABEL)?.takeIf { it.isNotBlank() } ?: "Destino"\n                mainHandler.post {\n                    selectDestination(SearchResult(LatLng(lat, lon), label), false)\n                    startNavigation()\n                }\n            }\n        }\n        ContextCompat.registerReceiver(\n            context,\n            receiver,\n            IntentFilter(ACTION_SMART_START_NAV),\n            ContextCompat.RECEIVER_NOT_EXPORTED\n        )\n        onDispose {\n            runCatching { context.unregisterReceiver(receiver) }\n            trackingListener?.let { try { locationManager.removeUpdates(it) } catch (_: Exception) {} }\n            demoRunnable?.let { mainHandler.removeCallbacks(it) }\n            tts.stop(); tts.shutdown()\n        }\n    }\n'''
if old_effect not in s:
    raise SystemExit('DisposableEffect anchor not found')
s = s.replace(old_effect, new_effect)

s = s.replace('NetherisGPS/8.0 Android', 'NetherisGPS/8.1 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text()
old_bg = '''    fun startBackgroundNow() {\n        val r = recent ?: return\n        if (!locationEnabled()) {\n            navMessage = "Activa la ubicación del teléfono"\n            return\n        }\n        val intent = Intent(context, NavigationForegroundService::class.java)\n            .setAction(NavigationForegroundService.ACTION_START)\n            .putExtra(NavigationForegroundService.EXTRA_LABEL, r.label)\n            .putExtra(NavigationForegroundService.EXTRA_LAT, r.lat)\n            .putExtra(NavigationForegroundService.EXTRA_LON, r.lon)\n        runCatching { ContextCompat.startForegroundService(context, intent) }\n            .onFailure { navMessage = "No pude iniciar navegación · revisa permiso de ubicación" }\n    }\n'''
new_bg = '''    fun startBackgroundNow() {\n        val r = recent ?: return\n        if (!locationEnabled()) {\n            navMessage = "Activa la ubicación del teléfono"\n            return\n        }\n        navMessage = "Katherine preparando ruta y navegación…"\n        val intent = Intent("cl.netheris.gps.SMART_START_NAV")\n            .setPackage(context.packageName)\n            .putExtra("smart_label", r.label)\n            .putExtra("smart_lat", r.lat)\n            .putExtra("smart_lon", r.lon)\n        runCatching { context.sendBroadcast(intent) }\n            .onFailure { navMessage = "No pude iniciar navegación" }\n    }\n'''
if old_bg not in t:
    raise SystemExit('Shell startBackgroundNow anchor not found')
t = t.replace(old_bg, new_bg)
t = t.replace('NETHERIS NAVIGATION AI · V8.0.1', 'NETHERIS NAVIGATION AI · V8.1')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 81', 'versionCode = 82').replace('versionName = "8.0.1"', 'versionName = "8.1.0"')
build.write_text(b)

print('Applied Netheris GPS v8.1 smart one-touch navigation')
