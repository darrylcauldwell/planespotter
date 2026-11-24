"""Tests for the streamed plain-English description of an aircraft."""
import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.config import settings
from app.schemas.aircraft import AircraftPosition, AircraftWithPosition
from app.services.llm import LLMClient, LLMError, LLMNotConfigured
from app.services.story import aircraft_facts, compass

TODAY = date(2026, 11, 24)


def _aircraft(position: AircraftPosition | None = None, **fields) -> AircraftWithPosition:
    """An A320 with the given position and any fields overridden."""
    values = {
        "icao24": "400a0b",
        "registration": "G-EZAA",
        "manufacturername": "Airbus",
        "model": "A320-214",
        "operator": "easyJet",
        "built": "2006-01-01",
    } | fields
    return AircraftWithPosition(**values, position=position, is_airborne=position is not None)


def _position(**fields) -> AircraftPosition:
    """A position at cruise, with any fields overridden."""
    values = {
        "icao24": "400a0b",
        "callsign": "EZY12AB ",
        "origin_country": "United Kingdom",
        "baro_altitude": 10668.0,
        "velocity": 231.5,
        "true_track": 270.0,
        "vertical_rate": 0.0,
        "on_ground": False,
    } | fields
    return AircraftPosition(**values)


async def _pieces(*texts):
    for text in texts:
        yield text


async def _fails(error: Exception, after: tuple = ()):
    for text in after:
        yield text
    raise error


class TestAircraftFacts:
    """Tests for the facts the model is given."""

    def test_in_flight_units_are_converted(self):
        """Test metres become feet, metres per second become knots, and the track a compass point."""
        facts = aircraft_facts(_aircraft(_position()), TODAY)

        assert "Altitude: 35,000 feet" in facts
        assert "Ground speed: 450 knots" in facts
        assert "Heading: west" in facts
        assert "Vertical: level" in facts
        assert "Callsign: EZY12AB\n" in facts
        assert "Country of registration: United Kingdom" in facts

    def test_climbing_rate_is_in_feet_per_minute(self):
        """Test a vertical rate is reported as climbing or descending in feet per minute."""
        assert "Vertical: climbing at 1,000 feet per minute" in aircraft_facts(_aircraft(_position(vertical_rate=5.08)), TODAY)
        assert "Vertical: descending at 1,000 feet per minute" in aircraft_facts(_aircraft(_position(vertical_rate=-5.08)), TODAY)

    def test_impossible_speed_is_left_out(self):
        """Test a bad decode's ground speed is not offered to the model, and the rest still is."""
        facts = aircraft_facts(_aircraft(_position(velocity=2103.26)), TODAY)

        assert "Ground speed" not in facts
        assert "Altitude: 35,000 feet" in facts

    def test_age_is_worked_out(self):
        """Test the year built carries the aircraft's age, from a date or a bare year."""
        assert "Built: 2006 (about 20 years ago)" in aircraft_facts(_aircraft(), TODAY)
        assert "Built: 1999 (about 27 years ago)" in aircraft_facts(_aircraft(built="1999"), TODAY)

    def test_missing_facts_are_left_out(self):
        """Test empty or unparseable fields are not offered to the model."""
        facts = aircraft_facts(_aircraft(operator="", built="unknown", owner=None), TODAY)

        assert "Operator" not in facts
        assert "Built" not in facts
        assert "Owner" not in facts

    def test_untracked_and_grounded_aircraft(self):
        """Test position facts are replaced by what is known when not flying."""
        assert "Live position: not currently tracked" in aircraft_facts(_aircraft(), TODAY)
        grounded = aircraft_facts(_aircraft(_position(on_ground=True)), TODAY)
        assert "Live position: on the ground" in grounded
        assert "Altitude" not in grounded

    @pytest.mark.parametrize("degrees, point", [(0, "north"), (22, "north"), (23, "north-east"), (180, "south"), (350, "north")])
    def test_compass(self, degrees, point):
        """Test a track angle maps to the nearest of eight compass points."""
        assert compass(degrees) == point


class TestStoryEndpoint:
    """Tests for GET /api/v1/aircraft/{icao24}/story."""

    @staticmethod
    def _service(aircraft):
        return MagicMock(return_value=MagicMock(get_by_icao24=AsyncMock(return_value=aircraft)))

    def test_streams_the_story(self, client):
        """Test the model's words are streamed back as plain text."""
        with patch("app.routers.story.AircraftService", self._service(_aircraft())), \
             patch("app.routers.story.tell_story", lambda aircraft: _pieces("An easyJet ", "A320.")):
            response = client.get("/api/v1/aircraft/400a0b/story")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert response.text == "An easyJet A320."

    def test_unknown_aircraft(self, client):
        """Test an unknown aircraft is a 404 and the model is never asked."""
        tell_story = MagicMock()
        with patch("app.routers.story.AircraftService", self._service(None)), \
             patch("app.routers.story.tell_story", tell_story):
            response = client.get("/api/v1/aircraft/ffffff/story")

        assert response.status_code == 404
        tell_story.assert_not_called()

    @pytest.mark.parametrize("error, status", [(LLMNotConfigured("off"), 503), (LLMError("down"), 502)])
    def test_model_failure_before_any_words(self, client, error, status):
        """Test a model that fails before writing anything gets a proper status code."""
        with patch("app.routers.story.AircraftService", self._service(_aircraft())), \
             patch("app.routers.story.tell_story", lambda aircraft: _fails(error)):
            response = client.get("/api/v1/aircraft/400a0b/story")

        assert response.status_code == status

    def test_model_failure_part_way(self, client):
        """Test a model that stops part way leaves the words so far and says so."""
        with patch("app.routers.story.AircraftService", self._service(_aircraft())), \
             patch("app.routers.story.tell_story", lambda aircraft: _fails(LLMError("cut"), ("An easyJet ",))):
            response = client.get("/api/v1/aircraft/400a0b/story")

        assert response.status_code == 200
        assert response.text.startswith("An easyJet ")
        assert "stopped before it finished" in response.text


class TestLLMClientStream:
    """Tests for streaming from an OpenAI-compatible server, against a fake one."""

    @pytest.fixture(autouse=True)
    def configured(self):
        with patch.object(settings, "llm_base_url", "http://llm:8080/v1"), \
             patch.object(settings, "llm_api_key", None):
            yield

    @staticmethod
    def _sse(*chunks: dict) -> bytes:
        events = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
        return (events + "data: [DONE]\n\n").encode()

    @staticmethod
    async def _collect(client: LLMClient) -> list[str]:
        return [piece async for piece in client.stream("story", [{"role": "user", "content": "q"}])]

    async def test_yields_each_piece_and_asks_for_a_stream(self):
        """Test content deltas are yielded in order and the request asks for streaming."""
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, content=self._sse(
                {"choices": [{"delta": {"role": "assistant"}}]},
                {"choices": [{"delta": {"content": "An easyJet "}}]},
                {"choices": [{"delta": {"content": "A320."}}]},
                {"choices": [], "usage": {"prompt_tokens": 200, "completion_tokens": 4}},
            ))

        pieces = await self._collect(LLMClient(transport=httpx.MockTransport(handler)))

        assert pieces == ["An easyJet ", "A320."]
        assert seen["body"]["stream"] is True

    @pytest.mark.parametrize(
        "response",
        [
            httpx.Response(500, text="model crashed"),
            httpx.Response(200, content=b"data: {not json\n\n"),
            httpx.Response(200, content=b'data: {"error": {"message": "context too long"}}\n\n'),
        ],
        ids=["server-error", "malformed-event", "error-event"],
    )
    async def test_failures_raise_llm_error(self, response):
        """Test every way a stream can fail surfaces as LLMError."""
        with pytest.raises(LLMError):
            await self._collect(LLMClient(transport=httpx.MockTransport(lambda request: response)))

    async def test_unconfigured_raises_on_first_piece(self):
        """Test a missing base URL is raised when the first piece is awaited."""
        with patch.object(settings, "llm_base_url", None), pytest.raises(LLMNotConfigured):
            await self._collect(LLMClient())
