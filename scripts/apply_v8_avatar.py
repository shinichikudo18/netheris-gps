from pathlib import Path
import base64

b64 = Path('scripts/katherine_avatar_v8.b64').read_text().strip()
raw = base64.b64decode(b64)
res = Path('app/src/main/res/drawable')
res.mkdir(parents=True, exist_ok=True)
(res / 'katherine_avatar.jpg').write_bytes(raw)

kt = Path('app/src/main/java/cl/netheris/gps/ui/KatherineAvatar.kt')
kt.write_text('''package cl.netheris.gps.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.matchParentSize
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import cl.netheris.gps.R

@Composable
fun KatherineAvatar(modifier: Modifier = Modifier, size: Dp = 42.dp) {
    Box(
        modifier = modifier
            .size(size)
            .clip(CircleShape)
            .border(2.dp, Color(0xFF5FE7FF), CircleShape),
        contentAlignment = Alignment.Center
    ) {
        Image(
            painter = painterResource(id = R.drawable.katherine_avatar),
            contentDescription = "Katherine",
            contentScale = ContentScale.Crop,
            modifier = Modifier.matchParentSize()
        )
    }
}
''')
print('Installed Katherine avatar as native drawable resource')
