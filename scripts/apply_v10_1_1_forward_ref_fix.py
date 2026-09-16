from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

old = '''        if ((navigationActive || coreActive) && searchPanelOpen) {\n            stopNavigation()\n            runCatching {\n                context.startService(Intent(context, NavigationForegroundService::class.java).setAction(NavigationForegroundService.ACTION_STOP))\n            }\n            navigationActive = false\n            coreActive = false\n            coreRestoreAttempted = false\n        }\n'''
new = '''        if ((navigationActive || coreActive) && searchPanelOpen) {\n            trackingListener?.let { try { locationManager.removeUpdates(it) } catch (_: Exception) {} }\n            trackingListener = null\n            demoRunnable?.let { mainHandler.removeCallbacks(it) }\n            demoRunnable = null\n            demoActive = false\n            navigationActive = false\n            runCatching {\n                context.startService(Intent(context, NavigationForegroundService::class.java).setAction(NavigationForegroundService.ACTION_STOP))\n            }\n            coreActive = false\n            coreRestoreAttempted = false\n        }\n'''
if old not in s:
    raise SystemExit('v10.1 selectDestination cleanup anchor not found')
s = s.replace(old, new)
main.write_text(s)
print('Applied v10.1 forward-reference fix')
