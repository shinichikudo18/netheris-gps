package cl.netheris.gps.core

import android.content.Context

object NavStateStore {
    private const val PREFS = "netheris_nav_state"

    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    data class Snapshot(
        val active: Boolean,
        val destination: String,
        val destinationLat: Double?,
        val destinationLon: Double?,
        val instruction: String,
        val nextDistance: String,
        val remaining: String,
        val eta: String,
        val speed: String,
        val updatedAt: Long
    )

    fun setDestination(context: Context, label: String, lat: Double, lon: Double) {
        prefs(context).edit()
            .putString("destination", label)
            .putLong("destination_lat", lat.toBits())
            .putLong("destination_lon", lon.toBits())
            .apply()
    }

    fun setActive(context: Context, active: Boolean) {
        prefs(context).edit().putBoolean("active", active).putLong("updated_at", System.currentTimeMillis()).apply()
    }

    fun update(
        context: Context,
        instruction: String,
        nextDistance: String,
        remaining: String,
        eta: String,
        speed: String
    ) {
        prefs(context).edit()
            .putBoolean("active", true)
            .putString("instruction", instruction)
            .putString("next_distance", nextDistance)
            .putString("remaining", remaining)
            .putString("eta", eta)
            .putString("speed", speed)
            .putLong("updated_at", System.currentTimeMillis())
            .apply()
    }

    fun snapshot(context: Context): Snapshot {
        val p = prefs(context)
        val hasLat = p.contains("destination_lat")
        val hasLon = p.contains("destination_lon")
        return Snapshot(
            active = p.getBoolean("active", false),
            destination = p.getString("destination", "") ?: "",
            destinationLat = if (hasLat) p.getLong("destination_lat", 0L).let(Double::fromBits) else null,
            destinationLon = if (hasLon) p.getLong("destination_lon", 0L).let(Double::fromBits) else null,
            instruction = p.getString("instruction", "") ?: "",
            nextDistance = p.getString("next_distance", "") ?: "",
            remaining = p.getString("remaining", "") ?: "",
            eta = p.getString("eta", "") ?: "",
            speed = p.getString("speed", "") ?: "",
            updatedAt = p.getLong("updated_at", 0L)
        )
    }

    fun clear(context: Context) {
        prefs(context).edit().clear().apply()
    }
}
