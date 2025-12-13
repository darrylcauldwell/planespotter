import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.database import engine
from app.services.redis_client import redis_client
from app.routers.aircraft import router as aircraft_router
from app.routers.health import router as health_router

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("Starting API server...")
    await redis_client.connect()
    logger.info("Connected to Redis")
    yield
    logger.info("Shutting down API server...")
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


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Planespotter API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
