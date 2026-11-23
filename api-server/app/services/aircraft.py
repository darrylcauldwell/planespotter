from collections.abc import Collection
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Text, all_, any_, bindparam, select, func
from sqlalchemy.dialects.postgresql import ARRAY
from app.models.aircraft import AircraftMetadata
from app.schemas.aircraft import AircraftPosition, AircraftWithPosition
from app.services.redis_client import redis_client


class AircraftService:
    """Business logic for aircraft operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        registration: str | None = None,
        icao24: str | None = None,
        manufacturer: str | None = None,
        model: str | None = None,
        operator: str | None = None,
        owner: str | None = None,
        airborne: bool | None = None,
        tracked: Collection[str] = (),
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[AircraftMetadata], int]:
        """Search aircraft with pagination.

        `airborne` keeps only aircraft in `tracked` (True) or only those not in it (False).
        """
        query = select(AircraftMetadata)

        # Apply filters
        if registration:
            query = query.where(
                AircraftMetadata.registration.ilike(f"%{registration}%")
            )
        if icao24:
            query = query.where(AircraftMetadata.icao24 == icao24.lower())
        if manufacturer:
            query = query.where(
                AircraftMetadata.manufacturername.ilike(f"%{manufacturer}%")
            )
        if model:
            query = query.where(AircraftMetadata.model.ilike(f"%{model}%"))
        if operator:
            query = query.where(AircraftMetadata.operator.ilike(f"%{operator}%"))
        if owner:
            query = query.where(AircraftMetadata.owner.ilike(f"%{owner}%"))
        if airborne is not None:
            # One array parameter, not one parameter per aircraft: worldwide traffic can pass
            # asyncpg's limit of 32,767 parameters.
            tracked_param = bindparam("tracked", value=list(tracked), type_=ARRAY(Text))
            if airborne:
                query = query.where(AircraftMetadata.icao24 == any_(tracked_param))
            else:
                query = query.where(AircraftMetadata.icao24 != all_(tracked_param))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)

        result = await self.db.execute(query)
        return result.scalars().all(), total or 0

    async def get_by_icao24(self, icao24: str) -> AircraftWithPosition | None:
        """Get aircraft metadata with live position."""
        query = select(AircraftMetadata).where(
            AircraftMetadata.icao24 == icao24.lower()
        )
        result = await self.db.execute(query)
        aircraft = result.scalar_one_or_none()

        if not aircraft:
            return None

        # Get live position from Redis
        position_data = await redis_client.get_aircraft_position(icao24)
        position = AircraftPosition(**position_data) if position_data else None

        return AircraftWithPosition(
            icao24=aircraft.icao24,
            registration=aircraft.registration,
            manufacturericao=aircraft.manufacturericao,
            manufacturername=aircraft.manufacturername,
            model=aircraft.model,
            typecode=aircraft.typecode,
            serialnumber=aircraft.serialnumber,
            linenumber=aircraft.linenumber,
            aircrafttype=aircraft.aircrafttype,
            operator=aircraft.operator,
            operatorcallsign=aircraft.operatorcallsign,
            operatoricao=aircraft.operatoricao,
            operatoriata=aircraft.operatoriata,
            owner=aircraft.owner,
            testreg=aircraft.testreg,
            registered=aircraft.registered,
            reguntil=aircraft.reguntil,
            status=aircraft.status,
            built=aircraft.built,
            firstflightdate=aircraft.firstflightdate,
            seatconfiguration=aircraft.seatconfiguration,
            engines=aircraft.engines,
            modes=aircraft.modes,
            adsb=aircraft.adsb,
            acars=aircraft.acars,
            notes=aircraft.notes,
            category=aircraft.category,
            position=position,
            is_airborne=position is not None,
        )
