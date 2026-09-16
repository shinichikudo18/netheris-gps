from pathlib import Path

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
s = shell.read_text()

s = s.replace('import android.content.Context\n', 'import android.Manifest\nimport android.content.Context\nimport android.content.pm.PackageManager\nimport android.location.LocationManager\n')
s = s.replace('import androidx.activity.compose.setContent\n', 'import androidx.activity.compose.rememberLauncherForActivityResult\nimport androidx.activity.compose.setContent\nimport androidx.activity.result.contract.ActivityResultContracts\n')

needle = '''    var snapshot by remember { mutableStateOf(NavStateStore.snapshot(context)) }\n    var recent by remember { mutableStateOf(latestRecent(context)) }\n'''
replace = '''    var snapshot by remember { mutableStateOf(NavStateStore.snapshot(context)) }\n    var recent by remember { mutableStateOf(latestRecent(context)) }\n    var navMessage by remember { mutableStateOf<String?>(null) }\n    var pendingAction by remember { mutableStateOf<String?>(null) }\n\n    fun hasLocationPermission(): Boolean =\n        ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||\n            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED\n\n    fun locationEnabled(): Boolean {\n        val lm = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager\n        return runCatching {\n            lm.isProviderEnabled(LocationManager.GPS_PROVIDER) || lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER)\n        }.getOrDefault(false)\n    }\n'''
if needle not in s:
    raise SystemExit('shell state anchor not found')
s = s.replace(needle, replace)

old_funcs = '''    fun startBackground() {\n        val r = recent ?: return\n        val intent = Intent(context, NavigationForegroundService::class.java)\n            .setAction(NavigationForegroundService.ACTION_START)\n            .putExtra(NavigationForegroundService.EXTRA_LABEL, r.label)\n            .putExtra(NavigationForegroundService.EXTRA_LAT, r.lat)\n            .putExtra(NavigationForegroundService.EXTRA_LON, r.lon)\n        ContextCompat.startForegroundService(context, intent)\n    }\n\n    fun resumeBackground() {\n        ContextCompat.startForegroundService(\n            context,\n            Intent(context, NavigationForegroundService::class.java).setAction(NavigationForegroundService.ACTION_RESUME)\n        )\n    }\n'''
new_funcs = '''    fun startBackgroundNow() {\n        val r = recent ?: return\n        if (!locationEnabled()) {\n            navMessage = "Activa la ubicación del teléfono"\n            return\n        }\n        val intent = Intent(context, NavigationForegroundService::class.java)\n            .setAction(NavigationForegroundService.ACTION_START)\n            .putExtra(NavigationForegroundService.EXTRA_LABEL, r.label)\n            .putExtra(NavigationForegroundService.EXTRA_LAT, r.lat)\n            .putExtra(NavigationForegroundService.EXTRA_LON, r.lon)\n        runCatching { ContextCompat.startForegroundService(context, intent) }\n            .onFailure { navMessage = "No pude iniciar navegación · revisa permiso de ubicación" }\n    }\n\n    fun resumeBackgroundNow() {\n        if (!locationEnabled()) {\n            navMessage = "Activa la ubicación del teléfono"\n            return\n        }\n        runCatching {\n            ContextCompat.startForegroundService(\n                context,\n                Intent(context, NavigationForegroundService::class.java).setAction(NavigationForegroundService.ACTION_RESUME)\n            )\n        }.onFailure { navMessage = "No pude reanudar navegación · revisa permiso de ubicación" }\n    }\n\n    val permissionLauncher = rememberLauncherForActivityResult(\n        ActivityResultContracts.RequestMultiplePermissions()\n    ) { permissions ->\n        val granted = permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true ||\n            permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true || hasLocationPermission()\n        val action = pendingAction\n        pendingAction = null\n        if (!granted) {\n            navMessage = "Katherine necesita permiso de ubicación para navegar"\n        } else {\n            navMessage = null\n            when (action) {\n                "start" -> startBackgroundNow()\n                "resume" -> resumeBackgroundNow()\n            }\n        }\n    }\n\n    fun startBackground() {\n        navMessage = null\n        if (hasLocationPermission()) startBackgroundNow() else {\n            pendingAction = "start"\n            permissionLauncher.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION))\n        }\n    }\n\n    fun resumeBackground() {\n        navMessage = null\n        if (hasLocationPermission()) resumeBackgroundNow() else {\n            pendingAction = "resume"\n            permissionLauncher.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION))\n        }\n    }\n'''
if old_funcs not in s:
    raise SystemExit('shell function anchor not found')
s = s.replace(old_funcs, new_funcs)

anchor = '''    when {\n        snapshot.active -> {\n'''
insert = '''    navMessage?.let { message ->\n        Text(\n            text = message,\n            color = Color(0xFFFFC0CB),\n            fontSize = 9.sp,\n            modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 2.dp)\n        )\n    }\n\n    when {\n        snapshot.active -> {\n'''
if anchor not in s:
    raise SystemExit('shell UI anchor not found')
s = s.replace(anchor, insert)
s = s.replace('NETHERIS NAVIGATION AI · V8.0', 'NETHERIS NAVIGATION AI · V8.0.1')
shell.write_text(s)

service = Path('app/src/main/java/cl/netheris/gps/nav/NavigationForegroundService.kt')
t = service.read_text()

old_start = '''    private fun startSession(lat: Double, lon: Double, label: String?) {\n        destination = P(lat, lon)\n        destinationLabel = label?.takeIf { it.isNotBlank() } ?: "Destino"\n        route = null\n        stepIndex = 0\n        NavStateStore.setDestination(this, destinationLabel, lat, lon)\n        NavStateStore.setActive(this, true)\n        startForeground(NOTIFICATION_ID, buildNotification("Preparando ruta…", destinationLabel))\n        startLocationTracking()\n    }\n'''
new_start = '''    private fun startSession(lat: Double, lon: Double, label: String?) {\n        if (!runtimeLocationReady()) {\n            NavStateStore.setActive(this, false)\n            stopSelf()\n            return\n        }\n        destination = P(lat, lon)\n        destinationLabel = label?.takeIf { it.isNotBlank() } ?: "Destino"\n        route = null\n        stepIndex = 0\n        NavStateStore.setDestination(this, destinationLabel, lat, lon)\n        NavStateStore.setActive(this, true)\n        if (!promoteToForeground("Preparando ruta…", destinationLabel)) return\n        startLocationTracking()\n    }\n'''
if old_start not in t:
    raise SystemExit('service startSession anchor not found')
t = t.replace(old_start, new_start)

old_restore = '''        route = null\n        stepIndex = 0\n        startForeground(NOTIFICATION_ID, buildNotification("Restaurando navegación…", destinationLabel))\n        startLocationTracking()\n        return true\n'''
new_restore = '''        route = null\n        stepIndex = 0\n        if (!runtimeLocationReady()) {\n            NavStateStore.setActive(this, false)\n            stopSelf()\n            return false\n        }\n        if (!promoteToForeground("Restaurando navegación…", destinationLabel)) return false\n        startLocationTracking()\n        return true\n'''
if old_restore not in t:
    raise SystemExit('service restore anchor not found')
t = t.replace(old_restore, new_restore)

anchor2 = '''    override fun onBind(intent: Intent?): IBinder? = null\n\n    private fun createChannel() {\n'''
helpers = '''    override fun onBind(intent: Intent?): IBinder? = null\n\n    private fun runtimeLocationReady(): Boolean {\n        val fine = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED\n        val coarse = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED\n        if (!fine && !coarse) return false\n        return runCatching {\n            locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER) ||\n                locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)\n        }.getOrDefault(false)\n    }\n\n    private fun promoteToForeground(title: String, text: String): Boolean {\n        return try {\n            startForeground(NOTIFICATION_ID, buildNotification(title, text))\n            true\n        } catch (_: Exception) {\n            NavStateStore.setActive(this, false)\n            stopSelf()\n            false\n        }\n    }\n\n    private fun createChannel() {\n'''
if anchor2 not in t:
    raise SystemExit('service helper anchor not found')
t = t.replace(anchor2, helpers)
t = t.replace('NetherisGPS/5.0 Android', 'NetherisGPS/8.0.1 Android')
service.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 80', 'versionCode = 81').replace('versionName = "8.0.0"', 'versionName = "8.0.1"')
build.write_text(b)

print('Applied Netheris GPS v8.0.1 Android 16 foreground-location hotfix')
