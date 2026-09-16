from pathlib import Path

# v15 integration events are published from NavStateStore, which is shared by
# phone UI, foreground navigation service and Android Auto. This script only
# wires the incoming deep-link command activity and bumps the generated build.

manifest = Path('app/src/main/AndroidManifest.xml')
m = manifest.read_text()
command_entry = '''        <activity
            android:name=".bridge.NetherisCommandActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="netheris" />
            </intent-filter>
        </activity>

'''
if '.bridge.NetherisCommandActivity' not in m:
    marker = '''        <activity
            android:name=".MainActivity"
            android:exported="false" />

'''
    if marker not in m:
        raise SystemExit('v15 manifest activity anchor not found')
    m = m.replace(marker, marker + command_entry, 1)
manifest.write_text(m)

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
