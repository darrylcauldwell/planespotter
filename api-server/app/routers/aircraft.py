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
    logger.info(f"Search request: status={params.status!r}, type={type(params.status)}")

    # If filtering by status, we need a different approach
    if params.status in ('airborne', 'ground'):
        logger.info(f"Applying status filter: {params.status}")
        # Get more results from DB, then filter by status
        aircraft_list, _ = await service.search(
            registration=params.registration,
            icao24=params.icao24,
            manufacturer=params.manufacturer,
            model=params.model,
            operator=params.operator,
            owner=params.owner,
            page=1,
            per_page=1000,  # Get more to filter from
        )

        # Filter by airborne status
        filtered_items = []
        for a in aircraft_list:
            is_airborne = await redis_client.is_airborne(a.icao24)
            if (params.status == 'airborne' and is_airborne) or (params.status == 'ground' and not is_airborne):
                item = AircraftBase.model_validate(a)
                item.is_airborne = is_airborne
                filtered_items.append(item)

        # Apply pagination to filtered results
        total = len(filtered_items)
        logger.info(f"Filtered to {total} aircraft with status={params.status}")
        pages = math.ceil(total / params.per_page) if total > 0 else 1
        start = (params.page - 1) * params.per_page
        end = start + params.per_page
        items = filtered_items[start:end]
    else:
        # Normal search without status filter
        aircraft_list, total = await service.search(
            registration=params.registration,
            icao24=params.icao24,
            manufacturer=params.manufacturer,
            model=params.model,
            operator=params.operator,
            owner=params.owner,
            page=params.page,
            per_page=params.per_page,
        )

        pages = math.ceil(total / params.per_page) if total > 0 else 1

        # Check airborne status for each aircraft
        items = []
        for a in aircraft_list:
            is_airborne = await redis_client.is_airborne(a.icao24)
            item = AircraftBase.model_validate(a)
            item.is_airborne = is_airborne
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
