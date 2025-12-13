import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.aircraft import (
    AircraftBase,
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
    registration: str | None = Query(None, description="Filter by registration"),
    icao24: str | None = Query(None, description="Filter by ICAO24 address"),
    manufacturer: str | None = Query(None, description="Filter by manufacturer"),
    model: str | None = Query(None, description="Filter by model"),
    operator: str | None = Query(None, description="Filter by operator"),
    owner: str | None = Query(None, description="Filter by owner"),
    status: str | None = Query(None, description="Filter by flight status: 'airborne' or 'ground'"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Search aircraft registry with pagination and filters."""
    service = AircraftService(db)
    logger.info(f"Search request: status={status!r}, type={type(status)}")

    # If filtering by status, we need a different approach
    if status in ('airborne', 'ground'):
        logger.info(f"Applying status filter: {status}")
        # Get more results from DB, then filter by status
        aircraft_list, _ = await service.search(
            registration=registration,
            icao24=icao24,
            manufacturer=manufacturer,
            model=model,
            operator=operator,
            owner=owner,
            page=1,
            per_page=1000,  # Get more to filter from
        )

        # Filter by airborne status
        filtered_items = []
        for a in aircraft_list:
            is_airborne = await redis_client.is_airborne(a.icao24)
            if (status == 'airborne' and is_airborne) or (status == 'ground' and not is_airborne):
                item = AircraftBase.model_validate(a)
                item.is_airborne = is_airborne
                filtered_items.append(item)

        # Apply pagination to filtered results
        total = len(filtered_items)
        logger.info(f"Filtered to {total} aircraft with status={status}")
        pages = math.ceil(total / per_page) if total > 0 else 1
        start = (page - 1) * per_page
        end = start + per_page
        items = filtered_items[start:end]
    else:
        # Normal search without status filter
        aircraft_list, total = await service.search(
            registration=registration,
            icao24=icao24,
            manufacturer=manufacturer,
            model=model,
            operator=operator,
            owner=owner,
            page=page,
            per_page=per_page,
        )

        pages = math.ceil(total / per_page) if total > 0 else 1

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
        page=page,
        per_page=per_page,
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
