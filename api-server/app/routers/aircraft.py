import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.aircraft import (
    AircraftBase,
    AircraftSearchParams,
    AircraftWithPosition,
    PaginatedResponse,
)
from app.services.aircraft import AircraftService
from app.services.redis_client import redis_client
import math

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/aircraft", tags=["aircraft"])


@router.get("", response_model=PaginatedResponse)
async def search_aircraft(
    params: Annotated[AircraftSearchParams, Query()],
    db: AsyncSession = Depends(get_db),
):
    """Search aircraft registry with pagination and filters."""
    service = AircraftService(db)

    # The status filter runs in the database against every tracked aircraft, so it covers all
    # matching rows and the total is exact. Any other status value means no status filter.
    airborne = {"airborne": True, "ground": False}.get(params.status)
    tracked = await redis_client.tracked_icao24s() if airborne is not None else []

    aircraft_list, total = await service.search(
        registration=params.registration,
        icao24=params.icao24,
        manufacturer=params.manufacturer,
        model=params.model,
        operator=params.operator,
        owner=params.owner,
        airborne=airborne,
        tracked=tracked,
        page=params.page,
        per_page=params.per_page,
    )
    pages = math.ceil(total / params.per_page) if total > 0 else 1

    airborne_on_page = await redis_client.airborne_among([a.icao24 for a in aircraft_list])
    items = []
    for a in aircraft_list:
        item = AircraftBase.model_validate(a)
        item.is_airborne = a.icao24 in airborne_on_page
        items.append(item)

    return PaginatedResponse(
        items=items,
        total=total,
        page=params.page,
        per_page=params.per_page,
        pages=pages,
    )


@router.get("/{icao24}", response_model=AircraftWithPosition)
async def get_aircraft(
    icao24: str,
    db: AsyncSession = Depends(get_db),
):
    """Get aircraft details with live position data."""
    service = AircraftService(db)
    aircraft = await service.get_by_icao24(icao24)

    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    return aircraft
