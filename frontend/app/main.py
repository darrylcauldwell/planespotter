import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from app.config import settings
from app.routers.pages import router as pages_router

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Planespotter",
    description="Aircraft tracking web interface",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(pages_router)

Instrumentator().instrument(app).expose(app)


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"status": "ok"}
