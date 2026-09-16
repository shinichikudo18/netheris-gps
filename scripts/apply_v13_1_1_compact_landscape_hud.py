from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()

# Compact the landscape maneuver HUD so more of the map stays visible.
s = s.replace('.fillMaxWidth(0.62f),', '.fillMaxWidth(0.50f),', 1)
s = s.replace('shape = RoundedCornerShape(20.dp),\n                        color = Color(0xE8091824),\n                        shadowElevation = 10.dp', 'shape = RoundedCornerShape(16.dp),\n                        color = Color(0xC9091824),\n                        shadowElevation = 8.dp', 1)
s = s.replace('Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 11.dp))', 'Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp))', 1)
s = s.replace('fontSize = 10.sp,\n                                    fontWeight = FontWeight.Black', 'fontSize = 9.sp,\n                                    fontWeight = FontWeight.Black', 1)
s = s.replace('Spacer(Modifier.height(5.dp))\n                            Row(', 'Spacer(Modifier.height(3.dp))\n                            Row(', 1)
s = s.replace('modifier = Modifier.fillMaxWidth(0.82f),\n                                    color = Color.White,\n                                    fontSize = 18.sp,', 'modifier = Modifier.fillMaxWidth(0.80f),\n                                    color = Color.White,\n                                    fontSize = 15.sp,', 1)
s = s.replace('color = Color(0xFF5FE7FF),\n                                    fontSize = 18.sp,', 'color = Color(0xFF5FE7FF),\n                                    fontSize = 16.sp,', 1)
s = s.replace('Spacer(Modifier.height(5.dp))\n                            Text(\n                                "$remainingInfo restante   ·   ETA $etaInfo   ·   $speedInfo",\n                                color = Color(0xFFA6C0D2),\n                                fontSize = 10.sp,', 'Spacer(Modifier.height(3.dp))\n                            Text(\n                                "$remainingInfo · ETA $etaInfo · $speedInfo",\n                                color = Color(0xFFA6C0D2),\n                                fontSize = 8.sp,', 1)
s = s.replace('Spacer(Modifier.height(5.dp))\n                            LinearProgressIndicator(', 'Spacer(Modifier.height(3.dp))\n                            LinearProgressIndicator(', 1)

# Make the Katherine status chip smaller too.
s = s.replace('shape = RoundedCornerShape(18.dp),\n                        color = Color(0xDD091722),\n                        shadowElevation = 8.dp', 'shape = RoundedCornerShape(15.dp),\n                        color = Color(0xC4091722),\n                        shadowElevation = 6.dp', 1)
s = s.replace('modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp),', 'modifier = Modifier.padding(horizontal = 8.dp, vertical = 5.dp),', 1)
s = s.replace('KatherineAvatar(size = 30.dp)', 'KatherineAvatar(size = 26.dp)', 1)
s = s.replace('Text("KATHERINE", color = Color.White, fontSize = 10.sp, fontWeight = FontWeight.Black)', 'Text("KATHERINE", color = Color.White, fontSize = 9.sp, fontWeight = FontWeight.Black)', 1)
s = s.replace('Text("NAV CORE · ONLINE", color = Color(0xFF69F7C8), fontSize = 7.sp, fontWeight = FontWeight.Bold)', 'Text("NAV CORE · ONLINE", color = Color(0xFF69F7C8), fontSize = 6.sp, fontWeight = FontWeight.Bold)', 1)

s = s.replace('NetherisGPS/13.1 Android', 'NetherisGPS/13.1.1 Android')
main.write_text(s)

shell = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
t = shell.read_text().replace('NETHERIS NAVIGATION AI · V13.1', 'NETHERIS NAVIGATION AI · V13.1.1')
shell.write_text(t)

build = Path('app/build.gradle.kts')
b = build.read_text().replace('versionCode = 132', 'versionCode = 133').replace('versionName = "13.1.0"', 'versionName = "13.1.1"')
build.write_text(b)

print('Applied Netheris GPS v13.1.1 compact landscape HUD')
