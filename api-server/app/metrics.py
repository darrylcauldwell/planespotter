from prometheus_client import Counter, Gauge, Histogram

SERVICE_UP = Gauge(
    "planespotter_service_up",
    "Whether a backend service is reachable (1=up, 0=down)",
    ["service"],
)
SERVICE_LATENCY = Histogram(
    "planespotter_service_latency_seconds",
    "Latency of health probe to a backend service",
    ["service"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
CACHE_HITS = Counter("planespotter_cache_hits_total", "Redis cache hits for position lookups")
CACHE_MISSES = Counter("planespotter_cache_misses_total", "Redis cache misses for position lookups")
AIRCRAFT_TRACKED = Gauge("planespotter_aircraft_tracked_total", "Aircraft positions currently in Redis")
