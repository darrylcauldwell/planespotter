import asyncio
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.config import settings
from app.database import engine
from app.metrics import SERVICE_UP, SERVICE_LATENCY, AIRCRAFT_TRACKED
from app.services.redis_client import redis_client
from app.routers.aircraft import router as aircraft_router
from app.routers.health import router as health_router

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _health_probe_loop():
    """Background loop that updates Prometheus metrics every 15s."""
    from app.routers.health import check_database

    while True:
        try:
            db_start = time.time()
            db_ok = await check_database()
            SERVICE_UP.labels(service="database").set(1 if db_ok else 0)
            SERVICE_LATENCY.labels(service="database").observe(time.time() - db_start)

            valkey_start = time.time()
            valkey_ok = await redis_client.ping()
            SERVICE_UP.labels(service="valkey").set(1 if valkey_ok else 0)
            SERVICE_LATENCY.labels(service="valkey").observe(time.time() - valkey_start)

            AIRCRAFT_TRACKED.set(await redis_client.get_tracked_count())
        except Exception as e:
            logger.warning(f"Health probe error: {e}")
        await asyncio.sleep(15)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("Starting API server...")
    await redis_client.connect()
    logger.info("Connected to Redis")
    probe_task = asyncio.create_task(_health_probe_loop())
    yield
    logger.info("Shutting down API server...")
    probe_task.cancel()
    await redis_client.disconnect()
    await engine.dispose()
    logger.info("Cleanup complete")


app = FastAPI(
    title="Planespotter API",
    description="Aircraft metadata and live position tracking API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(aircraft_router, prefix="/api/v1")

Instrumentator().instrument(app).expose(app)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Planespotter API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
