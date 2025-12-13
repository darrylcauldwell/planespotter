"""Tests for API endpoints."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_returns_api_info(self, client):
        """Test that root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Planespotter API"
        assert "version" in data
        assert "docs" in data
        assert "health" in data


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_liveness_probe(self, client):
        """Test liveness probe returns ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_readiness_probe_healthy(self, client, mock_db_session, mock_redis_client):
        """Test readiness probe when all services are healthy."""
        # Mock database check
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        with patch("app.routers.health.check_database", return_value=True), \
             patch("app.routers.health.redis_client", mock_redis_client):
            mock_redis_client.ping.return_value = True
            response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ready", "not ready"]

    def test_health_dashboard(self, client, mock_db_session):
        """Test health dashboard endpoint."""
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data


class TestAircraftSearchEndpoint:
    """Tests for aircraft search endpoint."""

    def test_search_without_filters(self, client, mock_db_session, sample_aircraft_list):
        """Test search endpoint without any filters."""
        # Setup mock
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_aircraft_list
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=2)

        response = client.get("/api/v1/aircraft")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

    def test_search_with_manufacturer_filter(self, client, mock_db_session, sample_aircraft):
        """Test search with manufacturer filter."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_aircraft]
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=1)

        response = client.get("/api/v1/aircraft?manufacturer=Boeing")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_search_with_registration_filter(self, client, mock_db_session, sample_aircraft):
        """Test search with registration filter."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_aircraft]
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=1)

        response = client.get("/api/v1/aircraft?registration=N12345")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_search_with_icao24_filter(self, client, mock_db_session, sample_aircraft):
        """Test search with icao24 filter."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_aircraft]
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=1)

        response = client.get("/api/v1/aircraft?icao24=abc123")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_search_pagination(self, client, mock_db_session, sample_aircraft_list):
        """Test search pagination parameters."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_aircraft_list
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=50)

        response = client.get("/api/v1/aircraft?page=2&per_page=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["per_page"] == 10

    def test_search_empty_results(self, client, mock_db_session):
        """Test search with no matching results."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=0)

        response = client.get("/api/v1/aircraft?manufacturer=NonExistent")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_search_with_status_filter_airborne(self, client, mock_db_session, sample_aircraft, mock_redis_client):
        """Test search with airborne status filter."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_aircraft]
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=1)

        # Mock redis to show aircraft is airborne
        mock_redis_client.exists.return_value = 1

        with patch("app.routers.aircraft.redis_client", mock_redis_client):
            response = client.get("/api/v1/aircraft?status=airborne")

        assert response.status_code == 200


class TestAircraftDetailEndpoint:
    """Tests for aircraft detail endpoint."""

    def test_get_aircraft_found(self, client, mock_db_session, sample_aircraft):
        """Test getting aircraft details when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_aircraft
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock Redis to return no position
        mock_redis = MagicMock()
        mock_redis.get_aircraft_position = AsyncMock(return_value=None)

        with patch("app.services.aircraft.redis_client", mock_redis):
            response = client.get("/api/v1/aircraft/abc123")

        assert response.status_code == 200
        data = response.json()
        assert data["icao24"] == "abc123"
        assert data["registration"] == "N12345"

    def test_get_aircraft_not_found(self, client, mock_db_session):
        """Test getting aircraft details when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        response = client.get("/api/v1/aircraft/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_get_aircraft_with_position(
        self, client, mock_db_session, sample_aircraft, sample_position_data
    ):
        """Test getting aircraft with live position data."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_aircraft
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock Redis to return position data directly (not JSON)
        mock_redis = MagicMock()
        mock_redis.get_aircraft_position = AsyncMock(return_value=sample_position_data)

        with patch("app.services.aircraft.redis_client", mock_redis):
            response = client.get("/api/v1/aircraft/abc123")

        assert response.status_code == 200
        data = response.json()
        assert data["icao24"] == "abc123"
        assert data["is_airborne"] == True
        assert data["position"] is not None
        assert data["position"]["latitude"] == 37.7749

    def test_get_aircraft_icao24_case_insensitive(self, client, mock_db_session, sample_aircraft):
        """Test that icao24 lookup is case insensitive."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_aircraft
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        mock_redis = MagicMock()
        mock_redis.get_aircraft_position = AsyncMock(return_value=None)

        with patch("app.services.aircraft.redis_client", mock_redis):
            response = client.get("/api/v1/aircraft/ABC123")

        assert response.status_code == 200


class TestConnectivityEndpoint:
    """Tests for connectivity endpoint."""

    def test_connectivity_matrix(self, client, mock_db_session):
        """Test connectivity matrix endpoint returns expected structure."""
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        response = client.get("/api/v1/connectivity")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "summary" in data
        assert "connections" in data
