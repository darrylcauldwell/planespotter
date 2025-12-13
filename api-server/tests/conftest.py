"""Shared test fixtures for API server tests."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models.aircraft import AircraftMetadata


@pytest.fixture
def sample_aircraft():
    """Create sample aircraft data."""
    return AircraftMetadata(
        icao24="abc123",
        registration="N12345",
        manufacturericao="BOEING",
        manufacturername="Boeing",
        model="737-800",
        typecode="B738",
        serialnumber="12345",
        linenumber="1234",
        aircrafttype="LandPlane",
        operator="Test Airlines",
        operatorcallsign="TEST",
        operatoricao="TST",
        operatoriata="TS",
        owner="Test Owner",
        testreg=None,
        registered="2020-01-01",
        reguntil="2025-01-01",
        status="Active",
        built="2019-01-01",
        firstflightdate="2019-06-01",
        seatconfiguration=None,
        engines="CFM56",
        modes="S",
        adsb="Y",
        acars=None,
        notes=None,
        category="A3",
    )


@pytest.fixture
def sample_aircraft_list(sample_aircraft):
    """Create a list of sample aircraft."""
    aircraft2 = AircraftMetadata(
        icao24="def456",
        registration="N67890",
        manufacturericao="AIRBUS",
        manufacturername="Airbus",
        model="A320-200",
        typecode="A320",
        serialnumber="67890",
        linenumber="5678",
        aircrafttype="LandPlane",
        operator="Another Airlines",
        operatorcallsign="ANOT",
        operatoricao="ANO",
        operatoriata="AN",
        owner="Another Owner",
        testreg=None,
        registered="2021-01-01",
        reguntil="2026-01-01",
        status="Active",
        built="2020-01-01",
        firstflightdate="2020-06-01",
        seatconfiguration=None,
        engines="CFM LEAP",
        modes="S",
        adsb="Y",
        acars=None,
        notes=None,
        category="A3",
    )
    return [sample_aircraft, aircraft2]


@pytest.fixture
def sample_position_data():
    """Create sample aircraft position data."""
    return {
        "icao24": "abc123",
        "callsign": "TST123",
        "origin_country": "United States",
        "time_position": 1699999999,
        "last_contact": 1699999999,
        "longitude": -122.4194,
        "latitude": 37.7749,
        "baro_altitude": 10000.0,
        "on_ground": False,
        "velocity": 250.0,
        "true_track": 180.0,
        "vertical_rate": 0.0,
        "geo_altitude": 10050.0,
        "squawk": "1200",
    }


@pytest.fixture
def mock_db_session():
    """Create a mock async database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock()
    client.get.return_value = None
    client.exists.return_value = 0
    client.ping.return_value = True
    return client


@pytest.fixture
def client(mock_db_session, mock_redis_client):
    """Create FastAPI test client with mocked dependencies."""

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db

    # Patch redis_client in the services module
    with patch("app.services.redis_client.redis_client", mock_redis_client), \
         patch("app.routers.aircraft.redis_client", mock_redis_client), \
         patch("app.routers.health.redis_client", mock_redis_client):
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_execute_result(sample_aircraft_list):
    """Create a mock for db.execute() result with scalars()."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = sample_aircraft_list
    mock_result.scalars.return_value = mock_scalars
    return mock_result


@pytest.fixture
def mock_scalar_one_result(sample_aircraft):
    """Create a mock for db.execute() with scalar_one_or_none()."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_aircraft
    return mock_result
