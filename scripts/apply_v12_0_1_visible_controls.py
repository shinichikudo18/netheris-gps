from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# v12 added the trip bar under the map. On Samsung/Android 16 this pushed the
# navigation dock below the visible viewport again. Reserve fixed space for
# the dock while keeping the route map useful.
old = '                                    immersiveMode -> 300.dp\n'
new = '                                    immersiveMode -> 220.dp\n'
if old not in s:
    raise SystemExit('immersive map height anchor not found')
s = s.replace(old, new, 1)

# Compact the trip bar a little so controls remain visible on smaller screens.
s = s.replace(
    'modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 7.dp),',
    'modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp),',
    1
)
s = s.replace('fontSize = 15.sp, fontWeight = FontWeight.Black', 'fontSize = 14.sp, fontWeight = FontWeight.Black', 1)
s = s.replace('fontSize = 14.sp, fontWeight = FontWeight.Black', 'fontSize = 13.sp, fontWeight = FontWeight.Black', 2)

# Version strings.
s = s.replace('NetherisGPS/12.0 Android', 'NetherisGPS/12.0.1 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text().replace('NETHERIS NAVIGATION AI · V12.0', 'NETHERIS NAVIGATION AI · V12.0.1')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 120', 'versionCode = 121').replace('versionName = "12.0.0"', 'versionName = "12.0.1"')
build.write_text(b)

print('Applied Netheris GPS v12.0.1 visible controls hotfix')
