package cl.netheris.gps.bridge

import android.content.Context
import android.location.Location
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

object NetherisBridge {
    private const val PREFS = "netheris_bridge"
    private const val KEY_ENABLED = "enabled"
    private const val KEY_URL = "url"
    private const val KEY_TOKEN = "token"
    private const val KEY_PRIVACY = "privacy"
    private const val KEY_QUEUE = "queue"
    private const val MAX_QUEUE = 30

    const val PRIVACY_STATUS = "status"
    const val PRIVACY_APPROX = "approx"
    const val PRIVACY_FULL = "full"

    private val executor = Executors.newSingleThreadExecutor()

    data class Config(
        val enabled: Boolean,
        val url: String,
        val token: String,
        val privacy: String
    )

    fun config(context: Context): Config {
        val p = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return Config(
            enabled = p.getBoolean(KEY_ENABLED, false),
            url = p.getString(KEY_URL, "") ?: "",
            token = p.getString(KEY_TOKEN, "") ?: "",
            privacy = p.getString(KEY_PRIVACY, PRIVACY_STATUS) ?: PRIVACY_STATUS
        )
    }

    fun configure(context: Context, enabled: Boolean, url: String, token: String = "", privacy: String = PRIVACY_STATUS) {
        val normalized = when (privacy) {
            PRIVACY_FULL, PRIVACY_APPROX -> privacy
            else -> PRIVACY_STATUS
        }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putBoolean(KEY_ENABLED, enabled)
            .putString(KEY_URL, url.trim())
            .putString(KEY_TOKEN, token.trim())
            .putString(KEY_PRIVACY, normalized)
            .apply()
        if (enabled) flush(context.applicationContext)
    }

    fun test(context: Context) {
        emit(context, "bridge_test", JSONObject().put("message", "Netheris GPS bridge online"))
    }

    fun emit(
        context: Context,
        event: String,
        navigation: JSONObject = JSONObject(),
        latitude: Double? = null,
        longitude: Double? = null
    ) {
        val app = context.applicationContext
        val cfg = config(app)
        if (!cfg.enabled || cfg.url.isBlank()) return

        val body = JSONObject()
            .put("event", event)
            .put("source", "netheris-gps")
            .put("version", "15.0")
            .put("timestamp", System.currentTimeMillis())
            .put("navigation", navigation)

        appendLocation(body, cfg.privacy, latitude, longitude)

        executor.execute {
            if (!post(cfg, body)) enqueue(app, body)
            else flushInternal(app, cfg)
        }
    }

    private fun appendLocation(body: JSONObject, privacy: String, lat: Double?, lon: Double?) {
        if (lat == null || lon == null) return
        when (privacy) {
            PRIVACY_FULL -> body.put("location", JSONObject().put("lat", lat).put("lon", lon).put("precision", "full"))
            PRIVACY_APPROX -> body.put(
                "location",
                JSONObject()
                    .put("lat", kotlin.math.round(lat * 1000.0) / 1000.0)
                    .put("lon", kotlin.math.round(lon * 1000.0) / 1000.0)
                    .put("precision", "approx")
            )
        }
    }

    private fun post(cfg: Config, body: JSONObject): Boolean {
        repeat(2) { attempt ->
            val conn = runCatching { URL(cfg.url).openConnection() as HttpURLConnection }.getOrNull() ?: return false
            try {
                conn.requestMethod = "POST"
                conn.connectTimeout = 7000
                conn.readTimeout = 7000
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json")
                conn.setRequestProperty("Accept", "application/json")
                conn.setRequestProperty("User-Agent", "NetherisGPS/15.0 Android")
                if (cfg.token.isNotBlank()) conn.setRequestProperty("Authorization", "Bearer ${cfg.token}")
                conn.outputStream.bufferedWriter().use { it.write(body.toString()) }
                if (conn.responseCode in 200..299) return true
            } catch (_: Exception) {
                // queued below after retry
            } finally {
                conn.disconnect()
            }
            if (attempt == 0) Thread.sleep(500L)
        }
        return false
    }

    private fun enqueue(context: Context, body: JSONObject) {
        val p = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val arr = runCatching { JSONArray(p.getString(KEY_QUEUE, "[]") ?: "[]") }.getOrDefault(JSONArray())
        val out = JSONArray()
        val start = (arr.length() - (MAX_QUEUE - 1)).coerceAtLeast(0)
        for (i in start until arr.length()) out.put(arr.optJSONObject(i))
        out.put(body)
        p.edit().putString(KEY_QUEUE, out.toString()).apply()
    }

    fun flush(context: Context) {
        val app = context.applicationContext
        val cfg = config(app)
        if (!cfg.enabled || cfg.url.isBlank()) return
        executor.execute { flushInternal(app, cfg) }
    }

    private fun flushInternal(context: Context, cfg: Config) {
        val p = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val arr = runCatching { JSONArray(p.getString(KEY_QUEUE, "[]") ?: "[]") }.getOrDefault(JSONArray())
        if (arr.length() == 0) return
        val remaining = JSONArray()
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            if (!post(cfg, item)) {
                for (j in i until arr.length()) arr.optJSONObject(j)?.let { remaining.put(it) }
                break
            }
        }
        p.edit().putString(KEY_QUEUE, remaining.toString()).apply()
    }

    fun distanceMeters(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Float {
        val result = FloatArray(1)
        Location.distanceBetween(lat1, lon1, lat2, lon2, result)
        return result[0]
    }
}
