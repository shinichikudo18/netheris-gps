from pathlib import Path

main = Path('app/src/main/java/cl/netheris/gps/MainActivity.kt')
s = main.read_text()
if 'import androidx.compose.ui.Alignment\n' not in s:
    s = s.replace('import androidx.compose.ui.Modifier\n', 'import androidx.compose.ui.Alignment\nimport androidx.compose.ui.Modifier\n')
main.write_text(s)
print('Applied v10 Alignment import fix')
