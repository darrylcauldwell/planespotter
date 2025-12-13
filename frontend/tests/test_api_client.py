"""Tests for APIClient."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.api_client import APIClient


class TestAPIClientSearchAircraft:
    """Tests for APIClient.search_aircraft() method."""

    @pytest.mark.asyncio
    async def test_search_aircraft_no_filters(self, sample_search_results):
        """Test search without filters."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_search_results
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            client = APIClient()
            client.base_url = "http://test-api:8080"
            result = await client.search_aircraft()

            assert result == sample_search_results
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert "http://test-api:8080/api/v1/aircraft" in str(call_args)

    @pytest.mark.asyncio
    async def test_search_aircraft_with_filters(self, sample_search_results):
        """Test search with manufacturer filter."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_search_results
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            client = APIClient()
            client.base_url = "http://test-api:8080"
            result = await client.search_aircraft(manufacturer="Boeing")

            assert result == sample_search_results
            call_args = mock_client.get.call_args
            params = call_args[1]["params"]
            assert params["manufacturer"] == "Boeing"

    @pytest.mark.asyncio
    async def test_search_aircraft_filters_none_values(self):
        """Test that None values are filtered from params."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": [], "total": 0, "page": 1, "per_page": 20}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            client = APIClient()
            client.base_url = "http://test-api:8080"
            await client.search_aircraft(
                manufacturer="Boeing",
                registration=None,
                icao24=None,
            )

            call_args = mock_client.get.call_args
            params = call_args[1]["params"]
            assert "manufacturer" in params
            assert "registration" not in params
            assert "icao24" not in params

    @pytest.mark.asyncio
    async def test_search_aircraft_with_pagination(self, sample_search_results):
        """Test search with pagination parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_search_results
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            client = APIClient()
            client.base_url = "http://test-api:8080"
            await client.search_aircraft(page=2, per_page=50)

            call_args = mock_client.get.call_args
            params = call_args[1]["params"]
            assert params["page"] == 2
            assert params["per_page"] == 50


class TestAPIClientGetAircraft:
    """Tests for APIClient.get_aircraft() method."""

    @pytest.mark.asyncio
    async def test_get_aircraft_found(self, sample_aircraft_data):
        """Test getting aircraft when found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_aircraft_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            client = APIClient()
            client.base_url = "http://test-api:8080"
            result = await client.get_aircraft("abc123")

            assert result == sample_aircraft_data
            mock_client.get.assert_called_once_with(
                "http://test-api:8080/api/v1/aircraft/abc123"
            )

    @pytest.mark.asyncio
    async def test_get_aircraft_not_found(self):
        """Test getting aircraft when not found returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            client = APIClient()
            client.base_url = "http://test-api:8080"
            result = await client.get_aircraft("nonexistent")

            assert result is None


class TestAPIClientGetHealth:
    """Tests for APIClient.get_health() method."""

    @pytest.mark.asyncio
    async def test_get_health_success(self, sample_health_data):
        """Test getting health data successfully."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_health_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            client = APIClient()
            client.base_url = "http://test-api:8080"
            result = await client.get_health()

            assert result == sample_health_data

    @pytest.mark.asyncio
    async def test_get_health_failure_returns_none(self):
        """Test that connection failure returns None."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            client = APIClient()
            client.base_url = "http://test-api:8080"
            result = await client.get_health()

            assert result is None


class TestAPIClientGetConnectivity:
    """Tests for APIClient.get_connectivity() method."""

    @pytest.mark.asyncio
    async def test_get_connectivity_success(self, sample_connectivity_data):
        """Test getting connectivity data successfully."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_connectivity_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            client = APIClient()
            client.base_url = "http://test-api:8080"
            result = await client.get_connectivity()

            assert result == sample_connectivity_data

    @pytest.mark.asyncio
    async def test_get_connectivity_failure_returns_none(self):
        """Test that connection failure returns None."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            client = APIClient()
            client.base_url = "http://test-api:8080"
            result = await client.get_connectivity()

            assert result is None
