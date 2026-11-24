"""Tests for the streamed description of an aircraft."""
import httpx
import pytest
from unittest.mock import MagicMock, patch


async def _pieces(*texts):
    for text in texts:
        yield text


async def _fails(error: Exception):
    raise error
    yield


def _status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "http://api/api/v1/aircraft/400a0b/story")
    return httpx.HTTPStatusError(str(status), request=request, response=httpx.Response(status, request=request))


class TestStoryRoute:
    """Tests for the story pass-through to the browser."""

    def test_streams_the_story_through(self, client, mock_api_client):
        """Test the API server's words reach the browser as plain text."""
        mock_api_client.story = MagicMock(return_value=_pieces("An easyJet ", "A320."))

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/aircraft/400a0b/story")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert response.text == "An easyJet A320."

    @pytest.mark.parametrize(
        "status, message",
        [(503, "switched off"), (404, "Aircraft not found"), (502, "could not describe")],
    )
    def test_api_errors_keep_their_status(self, client, mock_api_client, status, message):
        """Test the page can tell a missing model or aircraft from a failing model."""
        mock_api_client.story = MagicMock(return_value=_fails(_status_error(status)))

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/aircraft/400a0b/story")

        assert response.status_code == status
        assert message in response.text

    def test_unreachable_api_is_a_bad_gateway(self, client, mock_api_client):
        """Test a connection failure reads as the model being unable to answer."""
        mock_api_client.story = MagicMock(return_value=_fails(httpx.ConnectError("refused")))

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/aircraft/400a0b/story")

        assert response.status_code == 502


class TestDetailsPageStoryCard:
    """Tests for the story card on the aircraft page."""

    def test_details_page_offers_the_story(self, client, mock_api_client, sample_aircraft_data):
        """Test a found aircraft's page has the button that fetches its story."""
        mock_api_client.get_aircraft.return_value = sample_aircraft_data

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get(f"/aircraft/{sample_aircraft_data['icao24']}")

        assert response.status_code == 200
        assert 'id="story-button"' in response.text
        assert "/story" in response.text
