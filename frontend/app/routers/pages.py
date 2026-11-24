import logging
import httpx
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.services.api_client import api_client

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

MODEL_OFF = "The AI features are switched off: no language model is configured"


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home page."""
    return templates.TemplateResponse(request, "index.html")


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
    ask: str | None = Query(None),
):
    """Aircraft search page with results."""
    error = None
    results = None
    understood = None
    criteria = {
        "registration": registration,
        "icao24": icao24,
        "manufacturer": manufacturer,
        "model": model,
        "operator": operator,
        "owner": owner,
        "status": status,
    }

    # A question replaces the form: the model fills in the filters, and the page shows them so
    # the reader can see, and correct, what it understood.
    if ask:
        criteria = dict.fromkeys(criteria)
        try:
            understood = await api_client.ask(ask)
            criteria |= {name: understood["filters"].get(name) for name in criteria}
        except httpx.HTTPStatusError as e:
            logger.error(f"Ask failed: {e!r}")
            error = (
                MODEL_OFF
                if e.response.status_code == 503
                else "The language model could not answer that question"
            )
        except Exception as e:
            logger.error(f"Ask failed: {e!r}")
            error = "The language model could not answer that question"

    if any(criteria.values()):
        try:
            results = await api_client.search_aircraft(**criteria, page=page)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            error = "Failed to connect to API server"

    return templates.TemplateResponse(
        request,
        "search.html",
        {
            "results": results,
            "error": error,
            **{name: value or "" for name, value in criteria.items()},
            "page": page,
            "ask": ask or "",
            "understood": understood,
        },
    )


@router.get("/aircraft/{icao24}/story")
async def aircraft_story(icao24: str):
    """Pass the API server's streamed description of an aircraft through to the browser."""
    failed = "The language model could not describe this aircraft"
    pieces = api_client.story(icao24)
    # Wait for the first words before answering, so the page can tell a missing or failing
    # model from a slow one by the status code.
    try:
        first = await anext(pieces, "")
    except httpx.HTTPStatusError as e:
        logger.error(f"Story failed: {e!r}")
        status = e.response.status_code
        return PlainTextResponse({404: "Aircraft not found", 503: MODEL_OFF}.get(status, failed), status_code=status)
    except Exception as e:
        logger.error(f"Story failed: {e!r}")
        return PlainTextResponse(failed, status_code=502)

    async def story():
        yield first
        try:
            async for piece in pieces:
                yield piece
        except Exception as e:
            logger.error(f"Story stopped part way: {e!r}")

    return StreamingResponse(story(), media_type="text/plain; charset=utf-8")


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
        request,
        "details.html",
        {
            "aircraft": aircraft,
            "error": error,
            "icao24": icao24,
        },
    )


@router.get("/health", response_class=HTMLResponse)
async def health_page(request: Request):
    """Observability dashboard page."""
    health = await api_client.get_health()

    return templates.TemplateResponse(
        request,
        "health.html",
        {
            "health": health,
            "grafana_url": settings.grafana_url,
        },
    )


@router.get("/connectivity", response_class=HTMLResponse)
async def connectivity_page(request: Request):
    """Network connectivity visualization page for micro-segmentation demo."""
    connectivity = await api_client.get_connectivity()

    return templates.TemplateResponse(
        request,
        "connectivity.html",
        {
            "connectivity": connectivity,
        },
    )
