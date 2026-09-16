from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# In immersive navigation the 500dp map pushed the adaptive dock below the
# visible viewport on tall-density Samsung devices. Keep the map prominent,
# but reserve enough vertical room for the always-on navigation controls.
old = '''                                    immersiveMode -> 500.dp\n'''
new = '''                                    immersiveMode -> 300.dp\n'''
if old not in s:
    raise SystemExit('immersive map height anchor not found')
s = s.replace(old, new, 1)

# Make the status label truthful while the user has released camera follow.
s = s.replace(
    'Text("KATHERINE · MAPA EN SEGUIMIENTO", color = Color(0xFF6BE7FF), fontSize = 9.sp, fontWeight = FontWeight.Black)',
    'Text(if (cameraFollowEnabled) "KATHERINE · MAPA EN SEGUIMIENTO" else "KATHERINE · MAPA LIBRE", color = Color(0xFF6BE7FF), fontSize = 9.sp, fontWeight = FontWeight.Black)'
)

# Version strings.
s = s.replace('NetherisGPS/10.1 Android', 'NetherisGPS/10.1.1 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text().replace('NETHERIS NAVIGATION AI · V10.1', 'NETHERIS NAVIGATION AI · V10.1.1')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 101', 'versionCode = 102').replace('versionName = "10.1.0"', 'versionName = "10.1.1"')
build.write_text(b)

print('Applied Netheris GPS v10.1.1 visible navigation controls fix')
