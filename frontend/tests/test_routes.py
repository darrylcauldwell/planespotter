"""Tests for frontend page routes."""
import pytest
from unittest.mock import patch, AsyncMock


class TestHealthzEndpoint:
    """Tests for healthz endpoint."""

    def test_healthz_returns_ok(self, client):
        """Test healthz endpoint returns ok status."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestIndexPage:
    """Tests for index page."""

    def test_index_returns_html(self, client):
        """Test index page returns HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestSearchPage:
    """Tests for search page."""

    def test_search_page_without_query(self, client, mock_api_client):
        """Test search page renders without search query."""
        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/search")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # API should not be called without search params
        mock_api_client.search_aircraft.assert_not_called()

    def test_search_page_with_manufacturer_filter(
        self, client, mock_api_client, sample_search_results
    ):
        """Test search page with manufacturer filter."""
        mock_api_client.search_aircraft.return_value = sample_search_results

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/search?manufacturer=Boeing")

        assert response.status_code == 200
        mock_api_client.search_aircraft.assert_called_once()
        call_kwargs = mock_api_client.search_aircraft.call_args[1]
        assert call_kwargs["manufacturer"] == "Boeing"

    def test_search_page_with_status_filter(
        self, client, mock_api_client, sample_search_results
    ):
        """Test search page with airborne status filter."""
        mock_api_client.search_aircraft.return_value = sample_search_results

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/search?status=airborne")

        assert response.status_code == 200
        mock_api_client.search_aircraft.assert_called_once()
        call_kwargs = mock_api_client.search_aircraft.call_args[1]
        assert call_kwargs["status"] == "airborne"

    def test_search_page_with_pagination(
        self, client, mock_api_client, sample_search_results
    ):
        """Test search page with pagination."""
        mock_api_client.search_aircraft.return_value = sample_search_results

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/search?manufacturer=Boeing&page=2")

        assert response.status_code == 200
        call_kwargs = mock_api_client.search_aircraft.call_args[1]
        assert call_kwargs["page"] == 2

    def test_search_page_api_error(self, client, mock_api_client):
        """Test search page handles API errors gracefully."""
        mock_api_client.search_aircraft.side_effect = Exception("Connection failed")

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/search?manufacturer=Boeing")

        assert response.status_code == 200
        # Page should still render with error message


class TestAircraftDetailPage:
    """Tests for aircraft detail page."""

    def test_aircraft_detail_found(
        self, client, mock_api_client, sample_aircraft_data
    ):
        """Test aircraft detail page when aircraft found."""
        mock_api_client.get_aircraft.return_value = sample_aircraft_data

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/aircraft/abc123")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        mock_api_client.get_aircraft.assert_called_once_with("abc123")

    def test_aircraft_detail_not_found(self, client, mock_api_client):
        """Test aircraft detail page when aircraft not found."""
        mock_api_client.get_aircraft.return_value = None

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/aircraft/nonexistent")

        assert response.status_code == 200
        # Page renders but shows error message

    def test_aircraft_detail_api_error(self, client, mock_api_client):
        """Test aircraft detail page handles API errors."""
        mock_api_client.get_aircraft.side_effect = Exception("Connection failed")

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/aircraft/abc123")

        assert response.status_code == 200
        # Page should still render with error message


class TestHealthPage:
    """Tests for health dashboard page."""

    def test_health_page_with_data(self, client, mock_api_client, sample_health_data):
        """Test health page renders with health data."""
        mock_api_client.get_health.return_value = sample_health_data

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/health")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_health_page_no_data(self, client, mock_api_client):
        """Test health page renders when API returns None."""
        mock_api_client.get_health.return_value = None

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/health")

        assert response.status_code == 200

    def test_health_page_uses_default_grafana_url(self, client, mock_api_client, sample_health_data):
        """Test health page renders Grafana iframes with default URL."""
        mock_api_client.get_health.return_value = sample_health_data

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/health")

        assert response.status_code == 200
        html = response.text
        assert "http://localhost:3000/d/http-traffic" in html
        assert "http://localhost:3000/d/data-stores" in html
        assert "http://localhost:3000/d/container-metrics" in html
        assert "http://localhost:3000/d/planespotter-logs" in html

    def test_health_page_uses_custom_grafana_url(self, mock_api_client, sample_health_data):
        """Test health page renders Grafana iframes with custom URL."""
        mock_api_client.get_health.return_value = sample_health_data

        with patch("app.routers.pages.api_client", mock_api_client), \
             patch("app.routers.pages.settings") as mock_settings:
            mock_settings.grafana_url = "/grafana"
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app) as test_client:
                response = test_client.get("/health")

        assert response.status_code == 200
        html = response.text
        assert "/grafana/d/http-traffic" in html
        assert "/grafana/d/data-stores" in html
        assert "/grafana/d/container-metrics" in html
        assert "/grafana/d/planespotter-logs" in html
        # JS variable should also use custom URL
        assert "var GRAFANA_URL = '/grafana'" in html


class TestConnectivityPage:
    """Tests for connectivity page."""

    def test_connectivity_page_with_data(
        self, client, mock_api_client, sample_connectivity_data
    ):
        """Test connectivity page renders with data."""
        mock_api_client.get_connectivity.return_value = sample_connectivity_data

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/connectivity")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_connectivity_page_no_data(self, client, mock_api_client):
        """Test connectivity page renders when API returns None."""
        mock_api_client.get_connectivity.return_value = None

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/connectivity")

        assert response.status_code == 200
