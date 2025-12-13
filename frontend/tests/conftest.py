"""Shared test fixtures for frontend tests."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def sample_aircraft_data():
    """Sample aircraft data from API."""
    return {
        "icao24": "abc123",
        "registration": "N12345",
        "manufacturername": "Boeing",
        "model": "737-800",
        "operator": "Test Airlines",
        "owner": "Test Owner",
        "is_airborne": True,
        "position": {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 10000,
            "velocity": 250,
            "heading": 180,
        },
    }


@pytest.fixture
def sample_search_results(sample_aircraft_data):
    """Sample search results from API."""
    return {
        "items": [sample_aircraft_data],
        "total": 1,
        "page": 1,
        "per_page": 20,
        "pages": 1,
    }


@pytest.fixture
def sample_health_data():
    """Sample health data from API."""
    return {
        "status": "healthy",
        "services": {
            "database": {"status": "healthy", "latency_ms": 5},
            "redis": {"status": "healthy", "latency_ms": 2},
        },
    }


@pytest.fixture
def sample_connectivity_data():
    """Sample connectivity matrix from API."""
    return {
        "timestamp": "2024-01-01T00:00:00Z",
        "summary": {
            "total": 3,
            "connected": 3,
            "blocked": 0,
            "status": "healthy",
        },
        "connections": [
            {
                "id": "api-to-db",
                "source": "API Server",
                "destination": "PostgreSQL",
                "port": 5432,
                "protocol": "TCP",
                "status": "connected",
                "latency_ms": 10,
                "error": None,
            },
            {
                "id": "api-to-valkey",
                "source": "API Server",
                "destination": "Valkey",
                "port": 6379,
                "protocol": "TCP",
                "status": "connected",
                "latency_ms": 5,
                "error": None,
            },
            {
                "id": "api-to-opensky",
                "source": "API Server",
                "destination": "OpenSky Network",
                "port": 443,
                "protocol": "HTTPS",
                "status": "connected",
                "latency_ms": 150,
                "error": None,
            },
        ],
    }


@pytest.fixture
def mock_api_client():
    """Create a mock API client."""
    client = AsyncMock()
    client.search_aircraft.return_value = {
        "items": [],
        "total": 0,
        "page": 1,
        "per_page": 20,
    }
    client.get_aircraft.return_value = None
    client.get_health.return_value = None
    client.get_connectivity.return_value = None
    return client


@pytest.fixture
def client(mock_api_client):
    """Create FastAPI test client with mocked API client."""
    with patch("app.routers.pages.api_client", mock_api_client):
        with TestClient(app) as test_client:
            yield test_client
