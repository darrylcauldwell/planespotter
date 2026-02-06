from pydantic import BaseModel, Field


class AircraftBase(BaseModel):
    """Base aircraft metadata for list views."""

    icao24: str = Field(..., description="24-bit ICAO address in hex")
    registration: str | None = Field(None, description="Aircraft registration/tail number")
    manufacturername: str | None = Field(None, description="Manufacturer name")
    model: str | None = Field(None, description="Aircraft model")
    typecode: str | None = Field(None, description="ICAO type code")
    operator: str | None = Field(None, description="Operating airline/company")
    owner: str | None = Field(None, description="Registered owner")
    built: str | None = Field(None, description="Year manufactured")
    is_airborne: bool = Field(False, description="Whether aircraft is currently tracked")

    model_config = {"from_attributes": True}


class AircraftDetail(AircraftBase):
    """Full aircraft metadata with all fields."""

    manufacturericao: str | None = None
    serialnumber: str | None = None
    linenumber: str | None = None
    aircrafttype: str | None = None
    operatorcallsign: str | None = None
    operatoricao: str | None = None
    operatoriata: str | None = None
    testreg: str | None = None
    registered: str | None = None
    reguntil: str | None = None
    status: str | None = None
    firstflightdate: str | None = None
    seatconfiguration: str | None = None
    engines: str | None = None
    modes: str | None = None
    adsb: str | None = None
    acars: str | None = None
    notes: str | None = None
    category: str | None = None


class AircraftPosition(BaseModel):
    """Real-time aircraft position from OpenSky state vector."""

    icao24: str = Field(..., description="ICAO 24-bit address")
    callsign: str | None = Field(None, description="Callsign")
    origin_country: str | None = Field(None, description="Country of origin")
    time_position: int | None = Field(None, description="Unix timestamp of position")
    last_contact: int | None = Field(None, description="Unix timestamp of last contact")
    longitude: float | None = Field(None, description="WGS-84 longitude")
    latitude: float | None = Field(None, description="WGS-84 latitude")
    baro_altitude: float | None = Field(None, description="Barometric altitude in meters")
    on_ground: bool = Field(False, description="Whether aircraft is on ground")
    velocity: float | None = Field(None, description="Ground speed in m/s")
    true_track: float | None = Field(None, description="Track angle in degrees")
    vertical_rate: float | None = Field(None, description="Vertical rate in m/s")
    geo_altitude: float | None = Field(None, description="Geometric altitude in meters")
    squawk: str | None = Field(None, description="Transponder code")


class AircraftWithPosition(AircraftDetail):
    """Combined aircraft metadata with live position data."""

    position: AircraftPosition | None = Field(None, description="Current position if airborne")
    is_airborne: bool = Field(False, description="Whether aircraft is currently tracked")


class AircraftSearchParams(BaseModel):
    """Query parameters for aircraft search endpoint."""

    registration: str | None = Field(None, description="Filter by registration")
    icao24: str | None = Field(None, description="Filter by ICAO24 address")
    manufacturer: str | None = Field(None, description="Filter by manufacturer")
    model: str | None = Field(None, description="Filter by model")
    operator: str | None = Field(None, description="Filter by operator")
    owner: str | None = Field(None, description="Filter by owner")
    status: str | None = Field(None, description="Filter by flight status: 'airborne' or 'ground'")
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")

    model_config = {"extra": "forbid"}


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    items: list[AircraftBase]
    total: int = Field(..., description="Total number of matching records")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
