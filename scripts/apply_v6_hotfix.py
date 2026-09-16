from pathlib import Path

path = Path("app/src/main/java/cl/netheris/gps/ui/KatherineAvatar.kt")
text = path.read_text()
old = '''    val bitmap = remember {
        val bytes = Base64.decode(KATHERINE_AVATAR_B64, Base64.DEFAULT)
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size).asImageBitmap()
    }
    Image(
        bitmap = bitmap,
        contentDescription = "Katherine",
        contentScale = ContentScale.Crop,
        modifier = modifier
            .size(size)'''
new = '''    val bitmap = remember {
        runCatching {
            val bytes = Base64.decode(KATHERINE_AVATAR_B64, Base64.DEFAULT)
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
        }.getOrNull()
    }
    if (bitmap == null) {
        androidx.compose.material3.Surface(
            modifier = modifier
                .size(size)
                .clip(CircleShape)
                .border(2.dp, Color(0xFF5FE7FF), CircleShape),
            shape = CircleShape,
            color = Color(0xFF102334)
        ) {
            androidx.compose.foundation.layout.Box(
                contentAlignment = androidx.compose.ui.Alignment.Center
            ) {
                androidx.compose.material3.Text(
                    "K",
                    color = Color(0xFF5FE7FF),
                    fontWeight = androidx.compose.ui.text.font.FontWeight.Black
                )
            }
        }
        return
    }
    Image(
        bitmap = bitmap,
        contentDescription = "Katherine",
        contentScale = ContentScale.Crop,
        modifier = modifier
            .size(size)'''
if old not in text:
    raise SystemExit("KatherineAvatar pattern not found")
path.write_text(text.replace(old, new, 1))
print("Applied v6 avatar crash hotfix")
