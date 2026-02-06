import json
import redis.asyncio as redis
from app.config import settings
from app.metrics import CACHE_HITS, CACHE_MISSES


class RedisClient:
    """Async Redis client for aircraft position data."""

    def __init__(self):
        self._client: redis.Redis | None = None

    async def connect(self):
        """Initialize Redis connection."""
        self._client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )

    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()

    async def get_aircraft_position(self, icao24: str) -> dict | None:
        """Get live position for aircraft by ICAO24."""
        data = await self._client.get(f"aircraft:{icao24.lower()}")
        if data:
            CACHE_HITS.inc()
            return json.loads(data)
        CACHE_MISSES.inc()
        return None

    async def is_airborne(self, icao24: str) -> bool:
        """Check if aircraft is currently tracked."""
        return await self._client.exists(f"aircraft:{icao24.lower()}") > 0

    async def get_tracked_count(self) -> int:
        """Return the number of aircraft keys currently in Redis."""
        try:
            return await self._client.dbsize()
        except Exception:
            return 0

    async def ping(self) -> bool:
        """Health check for Redis connection."""
        try:
            return await self._client.ping()
        except Exception:
            return False


redis_client = RedisClient()
