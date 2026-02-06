from prometheus_client import Counter, Gauge, Histogram

SYNC_CYCLES_TOTAL = Counter("adsb_sync_cycles_total", "Total sync cycles", ["status"])
SYNC_DURATION_SECONDS = Histogram("adsb_sync_duration_seconds", "Full sync cycle duration",
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0, 60.0))
AIRCRAFT_STORED = Gauge("adsb_sync_aircraft_stored", "Aircraft positions stored in last sync")
OPENSKY_FETCH_DURATION = Histogram("adsb_sync_opensky_fetch_seconds", "OpenSky API fetch duration",
    buckets=(1.0, 2.5, 5.0, 10.0, 15.0, 30.0))
REDIS_STORE_DURATION = Histogram("adsb_sync_redis_store_seconds", "Redis pipeline store duration",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0))
CONSECUTIVE_FAILURES = Gauge("adsb_sync_consecutive_failures", "Consecutive fetch failures")
CURRENT_BACKOFF = Gauge("adsb_sync_current_backoff_seconds", "Current backoff interval")
