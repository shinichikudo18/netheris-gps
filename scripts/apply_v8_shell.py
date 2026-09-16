from pathlib import Path
p = Path('app/src/main/java/cl/netheris/gps/NetherisShellActivity.kt')
s = p.read_text()
s = s.replace('NETHERIS NAVIGATION AI · V6.0', 'NETHERIS NAVIGATION AI · V8.0')
s = s.replace('KATHERINE · GUÍA ACTIVA', 'KATHERINE · NAV CORE ACTIVO')
p.write_text(s)
print('Updated Netheris shell to v8')
