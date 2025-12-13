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


class TestRedisClientIsAirborne:
    """Tests for RedisClient.is_airborne() method."""

    @pytest.mark.asyncio
    async def test_is_airborne_true(self):
        """Test is_airborne returns True when key exists."""
        client = RedisClient()
        mock_redis_instance = AsyncMock()
        mock_redis_instance.exists.return_value = 1
        client._client = mock_redis_instance

        result = await client.is_airborne("abc123")

        assert result is True
        mock_redis_instance.exists.assert_called_once_with("aircraft:abc123")

    @pytest.mark.asyncio
    async def test_is_airborne_false(self):
        """Test is_airborne returns False when key doesn't exist."""
        client = RedisClient()
        mock_redis_instance = AsyncMock()
        mock_redis_instance.exists.return_value = 0
        client._client = mock_redis_instance

        result = await client.is_airborne("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_airborne_lowercase_conversion(self):
        """Test that icao24 is converted to lowercase."""
        client = RedisClient()
        mock_redis_instance = AsyncMock()
        mock_redis_instance.exists.return_value = 1
        client._client = mock_redis_instance

        await client.is_airborne("ABC123")

        # Should query with lowercase
        mock_redis_instance.exists.assert_called_once_with("aircraft:abc123")


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
