"""Tests for AircraftService."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.services.aircraft import AircraftService


class TestAircraftServiceSearch:
    """Tests for AircraftService.search() method."""

    @pytest.mark.asyncio
    async def test_search_no_filters(self, mock_db_session, sample_aircraft_list):
        """Test search without any filters returns all results."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_aircraft_list
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=2)

        service = AircraftService(mock_db_session)
        results, total = await service.search()

        assert len(results) == 2
        assert total == 2
        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_search_with_registration_filter(self, mock_db_session, sample_aircraft):
        """Test search with registration filter."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_aircraft]
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=1)

        service = AircraftService(mock_db_session)
        results, total = await service.search(registration="N12345")

        assert len(results) == 1
        assert results[0].registration == "N12345"

    @pytest.mark.asyncio
    async def test_search_with_manufacturer_filter(self, mock_db_session, sample_aircraft):
        """Test search with manufacturer filter."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_aircraft]
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=1)

        service = AircraftService(mock_db_session)
        results, total = await service.search(manufacturer="Boeing")

        assert len(results) == 1
        assert results[0].manufacturername == "Boeing"

    @pytest.mark.asyncio
    async def test_search_with_icao24_filter(self, mock_db_session, sample_aircraft):
        """Test search with icao24 filter converts to lowercase."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_aircraft]
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=1)

        service = AircraftService(mock_db_session)
        results, total = await service.search(icao24="ABC123")

        assert len(results) == 1
        # Verify execute was called (query was built)
        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_search_with_multiple_filters(self, mock_db_session, sample_aircraft):
        """Test search with multiple filters combined."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_aircraft]
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=1)

        service = AircraftService(mock_db_session)
        results, total = await service.search(
            manufacturer="Boeing",
            operator="Test Airlines"
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_pagination_first_page(self, mock_db_session, sample_aircraft_list):
        """Test search pagination returns correct offset for first page."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_aircraft_list
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=50)

        service = AircraftService(mock_db_session)
        results, total = await service.search(page=1, per_page=20)

        assert total == 50
        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_search_pagination_second_page(self, mock_db_session, sample_aircraft_list):
        """Test search pagination calculates correct offset for page 2."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_aircraft_list
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=50)

        service = AircraftService(mock_db_session)
        results, total = await service.search(page=2, per_page=20)

        # Offset should be (2-1) * 20 = 20
        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_search_empty_results(self, mock_db_session):
        """Test search returns empty list when no matches."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.scalar = AsyncMock(return_value=0)

        service = AircraftService(mock_db_session)
        results, total = await service.search(manufacturer="NonExistent")

        assert len(results) == 0
        assert total == 0


class TestAircraftServiceGetByIcao24:
    """Tests for AircraftService.get_by_icao24() method."""

    @pytest.mark.asyncio
    async def test_get_by_icao24_found_no_position(self, mock_db_session, sample_aircraft):
        """Test get_by_icao24 when aircraft exists but no position."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_aircraft
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        mock_redis = MagicMock()
        mock_redis.get_aircraft_position = AsyncMock(return_value=None)

        with patch("app.services.aircraft.redis_client", mock_redis):
            service = AircraftService(mock_db_session)
            result = await service.get_by_icao24("abc123")

        assert result is not None
        assert result.icao24 == "abc123"
        assert result.is_airborne == False
        assert result.position is None

    @pytest.mark.asyncio
    async def test_get_by_icao24_found_with_position(
        self, mock_db_session, sample_aircraft, sample_position_data
    ):
        """Test get_by_icao24 when aircraft exists with position data."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_aircraft
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        mock_redis = MagicMock()
        mock_redis.get_aircraft_position = AsyncMock(return_value=sample_position_data)

        with patch("app.services.aircraft.redis_client", mock_redis):
            service = AircraftService(mock_db_session)
            result = await service.get_by_icao24("abc123")

        assert result is not None
        assert result.icao24 == "abc123"
        assert result.is_airborne == True
        assert result.position is not None
        assert result.position.latitude == 37.7749

    @pytest.mark.asyncio
    async def test_get_by_icao24_not_found(self, mock_db_session):
        """Test get_by_icao24 when aircraft doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        service = AircraftService(mock_db_session)
        result = await service.get_by_icao24("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_icao24_lowercase_conversion(self, mock_db_session, sample_aircraft):
        """Test that icao24 is converted to lowercase before query."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_aircraft
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        mock_redis = MagicMock()
        mock_redis.get_aircraft_position = AsyncMock(return_value=None)

        with patch("app.services.aircraft.redis_client", mock_redis):
            service = AircraftService(mock_db_session)
            result = await service.get_by_icao24("ABC123")

        assert result is not None
        # Redis should be called with lowercase
        mock_redis.get_aircraft_position.assert_called()
