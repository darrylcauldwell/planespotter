"""Tests for RedisClient."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.services.redis_client import RedisClient


class TestRedisClientConnect:
    """Tests for RedisClient connection management."""

    @pytest.mark.asyncio
    async def test_connect_creates_client(self):
        """Test that connect initializes Redis client."""
        with patch("app.services.redis_client.redis.Redis") as mock_redis:
            mock_redis.return_value = MagicMock()

            client = RedisClient()
            await client.connect()

            mock_redis.assert_called_once()
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_disconnect_closes_client(self):
        """Test that disconnect closes the Redis connection."""
        client = RedisClient()
        mock_redis_instance = AsyncMock()
        client._client = mock_redis_instance

        await client.disconnect()

        mock_redis_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        """Test that disconnect handles no connection gracefully."""
        client = RedisClient()
        client._client = None

        # Should not raise
        await client.disconnect()


class TestRedisClientGetAircraftPosition:
    """Tests for RedisClient.get_aircraft_position() method."""

    @pytest.mark.asyncio
    async def test_get_aircraft_position_found(self, sample_position_data):
        """Test getting position when aircraft data exists."""
        client = RedisClient()
        mock_redis_instance = AsyncMock()
        mock_redis_instance.get.return_value = json.dumps(sample_position_data)
        client._client = mock_redis_instance

        result = await client.get_aircraft_position("abc123")

        assert result is not None
        assert result["icao24"] == "abc123"
        assert result["latitude"] == 37.7749
        mock_redis_instance.get.assert_called_once_with("aircraft:abc123")

    @pytest.mark.asyncio
    async def test_get_aircraft_position_not_found(self):
        """Test getting position when aircraft not in cache."""
        client = RedisClient()
        mock_redis_instance = AsyncMock()
        mock_redis_instance.get.return_value = None
        client._client = mock_redis_instance

        result = await client.get_aircraft_position("nonexistent")

        assert result is None
        mock_redis_instance.get.assert_called_once_with("aircraft:nonexistent")

    @pytest.mark.asyncio
    async def test_get_aircraft_position_lowercase_conversion(self, sample_position_data):
        """Test that icao24 is converted to lowercase."""
        client = RedisClient()
        mock_redis_instance = AsyncMock()
        mock_redis_instance.get.return_value = json.dumps(sample_position_data)
        client._client = mock_redis_instance

        await client.get_aircraft_position("ABC123")

        # Should query with lowercase
        mock_redis_instance.get.assert_called_once_with("aircraft:abc123")


class TestRedisClientAirborneAmong:
    """Tests for RedisClient.airborne_among() method."""

    @pytest.mark.asyncio
    async def test_returns_only_tracked_aircraft(self):
        """Test aircraft with a position are returned and the rest are not."""
        client = RedisClient()
        mock_redis_instance = AsyncMock()
        mock_redis_instance.mget.return_value = ['{"icao24": "abc123"}', None]
        client._client = mock_redis_instance

        result = await client.airborne_among(["abc123", "def456"])

        assert result == {"abc123"}

    @pytest.mark.asyncio
    async def test_one_round_trip_with_lowercase_keys(self):
        """Test every aircraft is looked up in a single MGET, by lowercase key."""
        client = RedisClient()
        mock_redis_instance = AsyncMock()
        mock_redis_instance.mget.return_value = [None, None]
        client._client = mock_redis_instance

        await client.airborne_among(["ABC123", "def456"])

        mock_redis_instance.mget.assert_called_once_with(["aircraft:abc123", "aircraft:def456"])

    @pytest.mark.asyncio
    async def test_empty_page_skips_valkey(self):
        """Test an empty list needs no round trip."""
        client = RedisClient()
        mock_redis_instance = AsyncMock()
        client._client = mock_redis_instance

        assert await client.airborne_among([]) == set()
        mock_redis_instance.mget.assert_not_called()


class TestRedisClientTrackedIcao24s:
    """Tests for RedisClient.tracked_icao24s() method."""

    @pytest.mark.asyncio
    async def test_lists_tracked_aircraft_with_scan(self):
        """Test every aircraft key is read with SCAN and returned without its prefix."""
        async def keys():
            for key in ["aircraft:abc123", "aircraft:def456"]:
                yield key

        client = RedisClient()
        mock_redis_instance = MagicMock()
        mock_redis_instance.scan_iter.return_value = keys()
        client._client = mock_redis_instance

        result = await client.tracked_icao24s()

        assert result == ["abc123", "def456"]
        assert mock_redis_instance.scan_iter.call_args.kwargs["match"] == "aircraft:*"


class TestRedisClientPing:
    """Tests for RedisClient.ping() method."""

    @pytest.mark.asyncio
    async def test_ping_success(self):
        """Test ping returns True when Redis responds."""
        client = RedisClient()
        mock_redis_instance = AsyncMock()
        mock_redis_instance.ping.return_value = True
        client._client = mock_redis_instance

        result = await client.ping()

        assert result is True

    @pytest.mark.asyncio
    async def test_ping_failure(self):
        """Test ping returns False when Redis connection fails."""
        client = RedisClient()
        mock_redis_instance = AsyncMock()
        mock_redis_instance.ping.side_effect = Exception("Connection refused")
        client._client = mock_redis_instance

        result = await client.ping()

        assert result is False
