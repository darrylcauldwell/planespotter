import logging
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.api_client import api_client

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home page."""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    registration: str | None = Query(None),
    icao24: str | None = Query(None),
    manufacturer: str | None = Query(None),
    model: str | None = Query(None),
    operator: str | None = Query(None),
    owner: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    """Aircraft search page with results."""
    error = None
    results = None
    has_search = any([registration, icao24, manufacturer, model, operator, owner, status])

    if has_search:
        try:
            results = await api_client.search_aircraft(
                registration=registration,
                icao24=icao24,
                manufacturer=manufacturer,
                model=model,
                operator=operator,
                owner=owner,
                status=status,
                page=page,
            )
        except Exception as e:
            logger.error(f"Search failed: {e}")
            error = "Failed to connect to API server"

    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "results": results,
            "error": error,
            "registration": registration or "",
            "icao24": icao24 or "",
            "manufacturer": manufacturer or "",
            "model": model or "",
            "operator": operator or "",
            "owner": owner or "",
            "status": status or "",
            "page": page,
        },
    )


@router.get("/aircraft/{icao24}", response_class=HTMLResponse)
async def aircraft_detail(request: Request, icao24: str):
    """Aircraft details page."""
    error = None
    aircraft = None

    try:
        aircraft = await api_client.get_aircraft(icao24)
        if not aircraft:
            error = f"Aircraft with ICAO24 '{icao24}' not found"
    except Exception as e:
        logger.error(f"Failed to get aircraft: {e}")
        error = "Failed to connect to API server"

    return templates.TemplateResponse(
        "details.html",
        {
            "request": request,
            "aircraft": aircraft,
            "error": error,
            "icao24": icao24,
        },
    )


@router.get("/health", response_class=HTMLResponse)
async def health_page(request: Request):
    """Health dashboard page."""
    health = await api_client.get_health()

    return templates.TemplateResponse(
        "health.html",
        {
            "request": request,
            "health": health,
        },
    )


@router.get("/connectivity", response_class=HTMLResponse)
async def connectivity_page(request: Request):
    """Network connectivity visualization page for micro-segmentation demo."""
    connectivity = await api_client.get_connectivity()

    return templates.TemplateResponse(
        "connectivity.html",
        {
            "request": request,
            "connectivity": connectivity,
        },
    )
