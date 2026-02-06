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

        tcp_ok = {"connected": True, "latency_ms": 1.0, "error": None}
        with patch("app.routers.health.check_tcp_connection", return_value=tcp_ok):
            response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert len(data["services"]) == 12
        critical = [s for s in data["services"] if s["critical"]]
        non_critical = [s for s in data["services"] if not s["critical"]]
        assert len(critical) == 5
        assert len(non_critical) == 7


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


class TestHealthDashboardConfigurable:
    """Tests for configurable service checks in health dashboard."""

    def test_health_dashboard_without_exporters(self, client, mock_db_session):
        """Test health dashboard excludes exporters when hosts are empty."""
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        tcp_ok = {"connected": True, "latency_ms": 1.0, "error": None}
        with patch("app.routers.health.settings") as mock_settings, \
             patch("app.routers.health.check_tcp_connection", return_value=tcp_ok):
            # Copy real defaults for fields used by health_dashboard
            mock_settings.database_host = "planespotter-db"
            mock_settings.database_port = 5432
            mock_settings.redis_host = "planespotter-cache"
            mock_settings.redis_port = 6379
            mock_settings.frontend_host = "planespotter-frontend"
            mock_settings.adsb_sync_host = "planespotter-sync"
            mock_settings.adsb_sync_port = 9090
            # Empty strings = skip exporter checks
            mock_settings.postgres_exporter_host = ""
            mock_settings.valkey_exporter_host = ""

            response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert len(data["services"]) == 10
        service_names = [s["name"] for s in data["services"]]
        assert "postgres-exporter" not in service_names
        assert "valkey-exporter" not in service_names

    def test_health_dashboard_uses_configured_hosts(self, client, mock_db_session):
        """Test health dashboard passes configured hosts to TCP checks."""
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        tcp_ok = {"connected": True, "latency_ms": 1.0, "error": None}
        with patch("app.routers.health.settings") as mock_settings, \
             patch("app.routers.health.check_tcp_connection", return_value=tcp_ok) as mock_tcp:
            mock_settings.database_host = "planespotter-db"
            mock_settings.database_port = 5432
            mock_settings.redis_host = "planespotter-cache"
            mock_settings.redis_port = 6379
            mock_settings.frontend_host = "planespotter-frontend"
            mock_settings.adsb_sync_host = "planespotter-sync"
            mock_settings.adsb_sync_port = 9090
            mock_settings.postgres_exporter_host = ""
            mock_settings.valkey_exporter_host = ""

            response = client.get("/api/v1/health")

        assert response.status_code == 200
        # Verify configured hosts were passed to TCP checks
        tcp_hosts_called = {call.args[0] for call in mock_tcp.call_args_list}
        assert "planespotter-frontend" in tcp_hosts_called
        assert "planespotter-sync" in tcp_hosts_called


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

    def test_connectivity_uses_configured_adsb_host(self, client, mock_db_session):
        """Test connectivity endpoint uses configured adsb-sync host and port."""
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        adsb_response = MagicMock()
        adsb_response.json.return_value = [
            {"id": "adsb-to-valkey", "source": "ADSB-Sync", "destination": "Valkey",
             "port": 6379, "protocol": "TCP", "status": "connected", "latency_ms": 1, "error": None},
        ]

        with patch("app.routers.health.settings") as mock_settings, \
             patch("app.routers.health.check_tcp_connection") as mock_tcp, \
             patch("httpx.AsyncClient") as mock_httpx:
            mock_settings.database_host = "planespotter-db"
            mock_settings.database_port = 5432
            mock_settings.redis_host = "planespotter-cache"
            mock_settings.redis_port = 6379
            mock_settings.adsb_sync_host = "planespotter-sync"
            mock_settings.adsb_sync_port = 9090

            mock_tcp.return_value = {"connected": True, "latency_ms": 1.0, "error": None}

            mock_client = AsyncMock()
            mock_client.get.return_value = adsb_response
            mock_httpx.return_value.__aenter__.return_value = mock_client

            response = client.get("/api/v1/connectivity")

        assert response.status_code == 200
        # Verify the adsb-sync URL used configured host/port
        mock_client.get.assert_called_once_with(
            "http://planespotter-sync:9090/connectivity", timeout=5.0
        )

    def test_connectivity_fallback_uses_configured_port(self, client, mock_db_session):
        """Test connectivity fallback uses configured redis port when adsb-sync unreachable."""
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        with patch("app.routers.health.settings") as mock_settings, \
             patch("app.routers.health.check_tcp_connection") as mock_tcp, \
             patch("httpx.AsyncClient") as mock_httpx:
            mock_settings.database_host = "planespotter-db"
            mock_settings.database_port = 5432
            mock_settings.redis_host = "planespotter-cache"
            mock_settings.redis_port = 7777
            mock_settings.adsb_sync_host = "planespotter-sync"
            mock_settings.adsb_sync_port = 9090

            mock_tcp.return_value = {"connected": True, "latency_ms": 1.0, "error": None}

            # Simulate adsb-sync being unreachable
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection refused")
            mock_httpx.return_value.__aenter__.return_value = mock_client

            response = client.get("/api/v1/connectivity")

        assert response.status_code == 200
        data = response.json()
        # Fallback adsb-to-valkey entry should use configured redis port
        adsb_valkey = next(c for c in data["connections"] if c["id"] == "adsb-to-valkey")
        assert adsb_valkey["port"] == 7777
