import asyncio
import json
import logging
import httpx
import redis.asyncio as redis
from app.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

OPENSKY_URL = "https://opensky-network.org/api/states/all"


async def fetch_states(client: httpx.AsyncClient) -> dict | None:
    """Fetch current aircraft states from OpenSky Network (anonymous access)."""
    try:
        response = await client.get(OPENSKY_URL, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        logger.warning("OpenSky API request timed out")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenSky API error: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch OpenSky data: {e}")
        return None


async def store_states(r: redis.Redis, states: list) -> int:
    """Store aircraft states in Redis with TTL."""
    count = 0
    pipe = r.pipeline()

    for state in states:
        if not state[0]:
            continue

        icao24 = state[0].lower()
        data = {
            "icao24": icao24,
            "callsign": state[1].strip() if state[1] else None,
            "origin_country": state[2],
            "time_position": state[3],
            "last_contact": state[4],
            "longitude": state[5],
            "latitude": state[6],
            "baro_altitude": state[7],
            "on_ground": state[8],
            "velocity": state[9],
            "true_track": state[10],
            "vertical_rate": state[11],
            "geo_altitude": state[13],
            "squawk": state[14],
        }
        pipe.setex(f"aircraft:{icao24}", settings.redis_ttl, json.dumps(data))
        count += 1

    await pipe.execute()
    return count


async def sync_loop():
    """Main sync loop polling OpenSky and updating Redis."""
    logger.info(f"Starting ADSB sync service")
    logger.info(f"Redis: {settings.redis_host}:{settings.redis_port}")
    logger.info(f"Poll interval: {settings.poll_interval}s, TTL: {settings.redis_ttl}s")

    r = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        decode_responses=True,
    )

    # Test Redis connection
    try:
        await r.ping()
        logger.info("Connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

    backoff = settings.poll_interval
    consecutive_failures = 0

    async with httpx.AsyncClient() as client:
        while True:
            logger.info("Fetching aircraft states from OpenSky...")
            data = await fetch_states(client)

            if data and "states" in data and data["states"]:
                count = await store_states(r, data["states"])
                logger.info(f"Stored {count} aircraft positions in Redis")
                consecutive_failures = 0
                backoff = settings.poll_interval
            else:
                consecutive_failures += 1
                if data and "states" in data:
                    logger.info("No aircraft data available")
                else:
                    logger.warning(f"Failed to get data (attempt {consecutive_failures})")
                    backoff = min(backoff * 2, settings.max_backoff)
                    logger.info(f"Backing off for {backoff}s")

            await asyncio.sleep(backoff)


def main():
    """Entry point."""
    try:
        asyncio.run(sync_loop())
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
