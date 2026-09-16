from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

old = '''    fun stopNavigation() {\n        trackingListener?.let { try { locationManager.removeUpdates(it) } catch (_: Exception) {} }\n        trackingListener = null\n        demoRunnable?.let { mainHandler.removeCallbacks(it) }\n        demoRunnable = null\n        navigationActive = false\n        demoActive = false\n        runCatching {\n            context.startService(\n                Intent(context, NavigationForegroundService::class.java)\n                    .setAction(NavigationForegroundService.ACTION_STOP)\n            )\n        }\n        status = "Navegación detenida"\n    }\n\n    fun resetToExploration() {\n        stopNavigation()\n'''
new = '''    fun stopNavigation() {\n        trackingListener?.let { try { locationManager.removeUpdates(it) } catch (_: Exception) {} }\n        trackingListener = null\n        demoRunnable?.let { mainHandler.removeCallbacks(it) }\n        demoRunnable = null\n        navigationActive = false\n        demoActive = false\n        status = "Navegación detenida"\n    }\n\n    fun resetToExploration() {\n        stopNavigation()\n        runCatching {\n            context.startService(\n                Intent(context, NavigationForegroundService::class.java)\n                    .setAction(NavigationForegroundService.ACTION_STOP)\n            )\n        }\n'''
if old not in s:
    raise SystemExit('v8.2.1 stop block not found')
s = s.replace(old, new)

s = s.replace('NetherisGPS/8.2.1 Android', 'NetherisGPS/8.2.2 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text().replace('NETHERIS NAVIGATION AI · V8.2.1', 'NETHERIS NAVIGATION AI · V8.2.2')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 84', 'versionCode = 85').replace('versionName = "8.2.1"', 'versionName = "8.2.2"')
build.write_text(b)

print('Applied Netheris GPS v8.2.2 start stability fix')
