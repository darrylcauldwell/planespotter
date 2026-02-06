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
        "timestamp": "2024-01-01T00:00:00Z",
        "services": [
            {"name": "database", "status": "healthy", "latency_ms": 5, "description": "PostgreSQL", "critical": True},
            {"name": "valkey", "status": "healthy", "latency_ms": 2, "description": "Cache", "critical": True},
            {"name": "api-server", "status": "healthy", "latency_ms": 1, "description": "FastAPI backend", "critical": True},
            {"name": "frontend", "status": "healthy", "latency_ms": 1, "description": "Web UI", "critical": True},
            {"name": "adsb-sync", "status": "healthy", "latency_ms": 1, "description": "ADS-B poller", "critical": True},
            {"name": "prometheus", "status": "healthy", "latency_ms": 1, "description": "Metrics store", "critical": False},
            {"name": "grafana", "status": "healthy", "latency_ms": 1, "description": "Dashboards", "critical": False},
            {"name": "loki", "status": "healthy", "latency_ms": 1, "description": "Log aggregator", "critical": False},
            {"name": "promtail", "status": "healthy", "latency_ms": 1, "description": "Log shipper", "critical": False},
            {"name": "cadvisor", "status": "healthy", "latency_ms": 1, "description": "Container metrics", "critical": False},
            {"name": "postgres-exporter", "status": "healthy", "latency_ms": 1, "description": "DB metrics", "critical": False},
            {"name": "valkey-exporter", "status": "healthy", "latency_ms": 1, "description": "Cache metrics", "critical": False},
        ],
    }


@pytest.fixture
def sample_connectivity_data():
    """Sample connectivity matrix from API."""
    return {
        "timestamp": "2024-01-01T00:00:00Z",
        "summary": {
            "total": 4,
            "connected": 4,
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
                "id": "adsb-to-valkey",
                "source": "ADSB-Sync",
                "destination": "Valkey",
                "port": 6379,
                "protocol": "TCP",
                "status": "connected",
                "latency_ms": 4,
                "error": None,
            },
            {
                "id": "adsb-to-opensky",
                "source": "ADSB-Sync",
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
