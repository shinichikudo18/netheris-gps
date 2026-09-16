from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# Fast cached-origin helper. getCurrentLocation() can take a long time indoors,
# leaving the UI apparently stuck at "Destino seleccionado". Use the freshest
# last-known GPS/network fix to start routing immediately when available.
anchor = '''    fun startNavigation() {\n'''
if anchor not in s:
    raise SystemExit('startNavigation anchor not found')
helper = r'''    fun cachedStartOrigin(): LatLng? {
        val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (!granted) return null
        return try {
            val gps = runCatching { locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER) }.getOrNull()
            val network = runCatching { locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER) }.getOrNull()
            val best = listOfNotNull(gps, network).maxByOrNull { it.time }
            best?.let { LatLng(it.latitude, it.longitude) }
        } catch (_: SecurityException) {
            null
        }
    }

'''
s = s.replace(anchor, helper + anchor, 1)

# Smart-start must support the optional intermediate stop too.
old_primary = '''private fun fetchPrimaryRoute(origin: LatLng, destination: LatLng): RouteResult? {\n    val url = "https://router.project-osrm.org/route/v1/driving/" +\n        "${origin.longitude},${origin.latitude};${destination.longitude},${destination.latitude}" +\n        "?overview=full&geometries=geojson&steps=true&alternatives=false"\n'''
new_primary = '''private fun fetchPrimaryRoute(origin: LatLng, destination: LatLng, via: LatLng? = null): RouteResult? {\n    val coordinates = if (via == null) {\n        "${origin.longitude},${origin.latitude};${destination.longitude},${destination.latitude}"\n    } else {\n        "${origin.longitude},${origin.latitude};${via.longitude},${via.latitude};${destination.longitude},${destination.latitude}"\n    }\n    val url = "https://router.project-osrm.org/route/v1/driving/" + coordinates +\n        "?overview=full&geometries=geojson&steps=true&alternatives=false"\n'''
if old_primary not in s:
    raise SystemExit('fetchPrimaryRoute anchor not found')
s = s.replace(old_primary, new_primary, 1)

# Use waypoint-aware primary route during one-touch start.
s = s.replace('val primary = fetchPrimaryRoute(origin, dest.point)', 'val primary = fetchPrimaryRoute(origin, dest.point, waypoint?.point)')

# Replace the location acquisition tail in smart-start. Prefer app state, then a
# cached provider fix, then request a fresh location. Always show visible progress.
old_tail = '''            lastLocation?.let(::prepare) ?: requestLocation { point ->\n                if (point != null) prepare(point) else status = "No pude obtener ubicación"\n            }\n            return\n'''
new_tail = '''            val originNow = lastLocation ?: cachedStartOrigin()\n            if (originNow != null) {\n                lastLocation = originNow\n                status = "Katherine calculando ruta…"\n                prepare(originNow)\n            } else {\n                status = "Obteniendo ubicación inicial…"\n                requestLocation { point ->\n                    if (point != null) prepare(point) else status = "No pude obtener ubicación · toca UBICACIÓN"\n                }\n            }\n            return\n'''
if old_tail not in s:
    raise SystemExit('smart-start location tail not found')
s = s.replace(old_tail, new_tail, 1)

# Make requestLocation visibly progress instead of silently waiting for Android.
request_anchor = '''        try {\n            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {\n'''
if request_anchor not in s:
    raise SystemExit('requestLocation try anchor not found')
s = s.replace(request_anchor, '''        try {\n            status = "Obteniendo ubicación…"\n            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {\n''', 1)

# Prefer NETWORK for the initial single fix because it is generally much faster
# indoors; continuous navigation still uses the normal live provider afterwards.
provider_old = '''                val provider = when {\n                    locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER\n                    locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER\n                    else -> null\n                }\n'''
provider_new = '''                val provider = when {\n                    locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER\n                    locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER\n                    else -> null\n                }\n'''
if provider_old in s:
    s = s.replace(provider_old, provider_new, 1)

# Version strings.
s = s.replace('NetherisGPS/13.0 Android', 'NetherisGPS/13.0.1 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text().replace('NETHERIS NAVIGATION AI · V13.0', 'NETHERIS NAVIGATION AI · V13.0.1')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 130', 'versionCode = 131').replace('versionName = "13.0.0"', 'versionName = "13.0.1"')
build.write_text(b)

print('Applied Netheris GPS v13.0.1 reliable start hotfix')
