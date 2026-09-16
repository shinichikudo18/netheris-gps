from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# Graphics + MapLibre icon helpers for a lightweight top-down Netheris car marker.
if 'import android.graphics.Bitmap\n' not in s:
    s = s.replace(
        'import android.content.pm.PackageManager\n',
        'import android.content.pm.PackageManager\nimport android.graphics.Bitmap\nimport android.graphics.Canvas\nimport android.graphics.Paint\nimport android.graphics.Path\nimport android.graphics.RectF\nimport android.graphics.Color as AndroidColor\n'
    )
if 'import org.maplibre.android.annotations.Icon\n' not in s:
    s = s.replace(
        'import org.maplibre.android.annotations.Marker\n',
        'import org.maplibre.android.annotations.Icon\nimport org.maplibre.android.annotations.IconFactory\nimport org.maplibre.android.annotations.Marker\n'
    )

# Top-down car icon. Kept programmatic to avoid another large drawable asset.
helper_anchor = '''private fun bearingBetween(a: LatLng, b: LatLng): Float {\n    val start = Location("start").apply { latitude = a.latitude; longitude = a.longitude }\n    val end = Location("end").apply { latitude = b.latitude; longitude = b.longitude }\n    return start.bearingTo(end)\n}\n'''
if helper_anchor not in s:
    raise SystemExit('bearingBetween anchor not found')
car_helper = helper_anchor + r'''

private fun createNavigationCarIcon(context: Context): Icon {
    val size = 96
    val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)

    val glow = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = AndroidColor.argb(70, 95, 231, 255)
        style = Paint.Style.FILL
    }
    canvas.drawCircle(48f, 50f, 38f, glow)

    val outline = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = AndroidColor.rgb(95, 231, 255)
        style = Paint.Style.STROKE
        strokeWidth = 5f
    }
    val body = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = AndroidColor.rgb(6, 22, 35)
        style = Paint.Style.FILL
    }
    val glass = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = AndroidColor.rgb(123, 226, 255)
        style = Paint.Style.FILL
    }
    val light = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = AndroidColor.WHITE
        style = Paint.Style.FILL
    }

    val carPath = Path().apply {
        moveTo(48f, 9f)
        lineTo(67f, 23f)
        lineTo(74f, 67f)
        quadTo(72f, 82f, 59f, 86f)
        lineTo(37f, 86f)
        quadTo(24f, 82f, 22f, 67f)
        lineTo(29f, 23f)
        close()
    }
    canvas.drawPath(carPath, body)
    canvas.drawPath(carPath, outline)
    canvas.drawRoundRect(RectF(34f, 28f, 62f, 48f), 7f, 7f, glass)
    canvas.drawRoundRect(RectF(33f, 56f, 63f, 72f), 6f, 6f, Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = AndroidColor.rgb(31, 61, 83)
        style = Paint.Style.FILL
    })
    canvas.drawCircle(35f, 18f, 4f, light)
    canvas.drawCircle(61f, 18f, 4f, light)

    return IconFactory.getInstance(context).fromBitmap(bitmap)
}
'''
s = s.replace(helper_anchor, car_helper, 1)

# Cache icons + camera update timing once per composition.
state_anchor = '    var arrivedDestination by remember { mutableStateOf<SearchResult?>(null) }\n'
if state_anchor not in s:
    raise SystemExit('v10 state anchor not found')
s = s.replace(
    state_anchor,
    state_anchor +
    '    val navigationCarIcon = remember { createNavigationCarIcon(context) }\n'
    '    val defaultLocationIcon = remember { IconFactory.getInstance(context).defaultMarker() }\n'
    '    var lastCameraUpdateAt by remember { mutableStateOf(0L) }\n'
)

# Update one marker instead of deleting + re-adding it on every GPS tick.
old_marker = '''        locationMarker?.let { readyMap.removeMarker(it) }\n        locationMarker = readyMap.addMarker(MarkerOptions().position(latLng).title(if (demoActive) "Demo" else "Mi ubicación"))\n        val isNav = navigationActive || demoActive\n'''
new_marker = '''        val isNav = navigationActive || demoActive\n        val desiredIcon = if (isNav) navigationCarIcon else defaultLocationIcon\n        val marker = locationMarker\n        if (marker == null) {\n            locationMarker = readyMap.addMarker(\n                MarkerOptions()\n                    .position(latLng)\n                    .title(if (demoActive) "Demo" else if (isNav) "Netheris Vehicle" else "Mi ubicación")\n                    .icon(desiredIcon)\n            )\n        } else {\n            marker.position = latLng\n            marker.title = if (demoActive) "Demo" else if (isNav) "Netheris Vehicle" else "Mi ubicación"\n            marker.icon = desiredIcon\n            readyMap.updateMarker(marker)\n        }\n'''
if old_marker not in s:
    raise SystemExit('showLocation marker anchor not found')
s = s.replace(old_marker, new_marker, 1)

# Throttle camera animations a little in demo/high-frequency updates; location marker still updates every tick.
old_follow = '''        val shouldFollow = moveCamera && (!isNav || cameraFollowEnabled)\n        if (shouldFollow) {\n'''
new_follow = '''        val now = SystemClock.elapsedRealtime()\n        val cameraDue = !isNav || now - lastCameraUpdateAt >= 500L\n        val shouldFollow = moveCamera && (!isNav || cameraFollowEnabled) && cameraDue\n        if (shouldFollow) {\n            lastCameraUpdateAt = now\n'''
if old_follow not in s:
    raise SystemExit('camera follow anchor not found')
s = s.replace(old_follow, new_follow, 1)

# Smoother/snappier camera transition.
s = s.replace('readyMap.animateCamera(CameraUpdateFactory.newCameraPosition(builder.build()), 320)', 'readyMap.animateCamera(CameraUpdateFactory.newCameraPosition(builder.build()), 240)', 1)

# Avoid aggressive rerouting loops when GPS accuracy is noisy.
s = s.replace('SystemClock.elapsedRealtime() - lastRerouteAt > 15000L', 'SystemClock.elapsedRealtime() - lastRerouteAt > 22000L')

# Keep dock labels on one line on narrower phones.
s = s.replace('Text("CENTRAR", fontSize = 8.sp, fontWeight = FontWeight.Black)', 'Text("CENTRAR", fontSize = 7.sp, fontWeight = FontWeight.Black, maxLines = 1)')
s = s.replace('Text(if (searchPanelOpen) "MAPA" else "BUSCAR", fontSize = 8.sp, fontWeight = FontWeight.Black)', 'Text(if (searchPanelOpen) "MAPA" else "BUSCAR", fontSize = 7.sp, fontWeight = FontWeight.Black, maxLines = 1)')

# Version strings.
s = s.replace('NetherisGPS/10.1.1 Android', 'NetherisGPS/11.0 Android')
main.write_text(s)

# Background service: slightly lower GPS churn and throttle state/notification writes.
service = Path('app/src/main/java/cl/netheris/gps/nav/NavigationForegroundService.kt')
t = service.read_text()

field_anchor = '    private var lastReroute = 0L\n'
if field_anchor not in t:
    raise SystemExit('service lastReroute anchor not found')
t = t.replace(field_anchor, field_anchor + '    private var lastPresentationUpdate = 0L\n')

t = t.replace('locationManager.requestLocationUpdates(provider, 1500L, 4f, l, Looper.getMainLooper())', 'locationManager.requestLocationUpdates(provider, 2000L, 5f, l, Looper.getMainLooper())')

old_present = '''        NavStateStore.update(this, instruction, next, formatDistance(remaining), eta, "${max(0, speed.toInt())} km/h")\n        updateNotification(if (next.isBlank()) instruction else "$instruction · $next", "$destinationLabel · ${formatDistance(remaining)} · ETA $eta")\n'''
new_present = '''        val presentationNow = SystemClock.elapsedRealtime()\n        if (presentationNow - lastPresentationUpdate >= 1800L) {\n            lastPresentationUpdate = presentationNow\n            NavStateStore.update(this, instruction, next, formatDistance(remaining), eta, "${max(0, speed.toInt())} km/h")\n            updateNotification(if (next.isBlank()) instruction else "$instruction · $next", "$destinationLabel · ${formatDistance(remaining)} · ETA $eta")\n        }\n'''
if old_present not in t:
    raise SystemExit('service presentation anchor not found')
t = t.replace(old_present, new_present, 1)
t = t.replace('now - lastReroute > 15000L', 'now - lastReroute > 22000L')
t = t.replace('NetherisGPS/8.0.1 Android', 'NetherisGPS/11.0 Android')
service.write_text(t)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
u = shell.read_text().replace('NETHERIS NAVIGATION AI · V10.1.1', 'NETHERIS NAVIGATION AI · V11.0')
shell.write_text(u)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 102', 'versionCode = 110').replace('versionName = "10.1.1"', 'versionName = "11.0.0"')
build.write_text(b)

print('Applied Netheris GPS v11 navigation core optimization + car marker')
