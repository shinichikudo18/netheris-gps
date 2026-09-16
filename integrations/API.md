# Netheris GPS v15 Integration API

Netheris GPS v15 exposes a small integration layer designed for n8n, Home Assistant, Katherine, dashboards, or other Netheris services.

## Outbound webhook

Configure locally in Android code with:

```kotlin
NetherisBridge.configure(
    context = context,
    enabled = true,
    url = "https://YOUR-ENDPOINT/webhook/netheris-gps",
    token = "OPTIONAL_BEARER_TOKEN",
    privacy = NetherisBridge.PRIVACY_STATUS
)
```

Privacy modes:

- `status`: sends navigation state only; no coordinates.
- `approx`: sends rounded coordinates (~100 m class precision).
- `full`: sends full coordinates.

Do not commit real URLs, tokens, home coordinates, or other private values to GitHub.

### Events

`navigation_started`

```json
{
  "event": "navigation_started",
  "source": "netheris-gps",
  "version": "15.0",
  "timestamp": 0,
  "navigation": {
    "active": true,
    "destination": "Casa",
    "destination_lat": -33.0,
    "destination_lon": -70.0
  }
}
```

`navigation_updated` is emitted at most every ~15 seconds while navigating and may include instruction, next distance, remaining distance, ETA and speed.

`approaching_home` is emitted once per session when entering approximately 5 km, 2 km and 500 m from the locally saved Home coordinate.

`arrived` is emitted when the active destination is reached.

`navigation_stopped` is emitted when navigation is manually stopped.

`bridge_test` can be generated with `NetherisBridge.test(context)`.

If delivery fails, v15 keeps a local FIFO queue of up to 30 pending bridge events and retries later when a subsequent delivery succeeds or `flush()` is called.

## Incoming commands

Android deep links allow another local app, Tasker, a dashboard, or a future Netheris companion app to control the GPS without coupling to its UI.

Navigate:

```text
netheris://navigate?lat=-33.45&lon=-70.66&label=Casa
```

Stop navigation:

```text
netheris://stop
```

Bridge connectivity test:

```text
netheris://bridge-test
```

For security, bridge URL/token configuration is deliberately not accepted through deep links. Configure secrets locally or through a future secure settings screen.

## Suggested n8n flow

Webhook -> Switch on `event` -> Home Assistant / Katherine / notifications / dashboard.

Examples:

- `navigation_started`: set `input_boolean.netheris_navigating` on.
- `navigation_updated`: update ETA/distance entities.
- `approaching_home` with `threshold_meters=2000`: trigger home preparation automation.
- `arrived`: update presence/arrival workflow.
- `navigation_stopped`: clear trip state.

## Suggested Home Assistant entities

- `sensor.netheris_gps_destination`
- `sensor.netheris_gps_eta`
- `sensor.netheris_gps_remaining`
- `sensor.netheris_gps_speed`
- `binary_sensor.netheris_gps_navigating`
- optional `device_tracker.netheris_gps` only when privacy mode is `approx` or `full`.
