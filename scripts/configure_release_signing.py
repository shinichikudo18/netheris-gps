from pathlib import Path

build = Path('app/build.gradle.kts')
b = build.read_text()

b = b.replace('versionCode = 150', 'versionCode = 151')
b = b.replace('versionName = "15.0.0"', 'versionName = "15.1.0"')

if 'NETHERIS_STORE_FILE' not in b:
    signing = '''    val netherisStoreFile = System.getenv("NETHERIS_STORE_FILE")\n    val netherisStorePassword = System.getenv("NETHERIS_STORE_PASSWORD")\n    val netherisKeyAlias = System.getenv("NETHERIS_KEY_ALIAS")\n    val netherisKeyPassword = System.getenv("NETHERIS_KEY_PASSWORD")\n\n    signingConfigs {\n        create("netherisRelease") {\n            storeFile = file(requireNotNull(netherisStoreFile) { "NETHERIS_STORE_FILE missing" })\n            storePassword = requireNotNull(netherisStorePassword) { "NETHERIS_STORE_PASSWORD missing" }\n            keyAlias = requireNotNull(netherisKeyAlias) { "NETHERIS_KEY_ALIAS missing" }\n            keyPassword = requireNotNull(netherisKeyPassword) { "NETHERIS_KEY_PASSWORD missing" }\n            enableV1Signing = true\n            enableV2Signing = true\n            enableV3Signing = true\n        }\n    }\n\n'''
    b = b.replace('    buildTypes {\n', signing + '    buildTypes {\n', 1)
    b = b.replace('        release {\n            isMinifyEnabled = false\n', '        release {\n            signingConfig = signingConfigs.getByName("netherisRelease")\n            isMinifyEnabled = false\n', 1)

build.write_text(b)

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text().replace('NetherisGPS/15.0 Android', 'NetherisGPS/15.1 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text().replace('NETHERIS NAVIGATION AI · V15.0', 'NETHERIS NAVIGATION AI · V15.1')
shell.write_text(t)

print('Configured Netheris GPS v15.1 signed release')
