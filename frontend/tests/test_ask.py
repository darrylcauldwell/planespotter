"""Tests for asking Planespotter in plain English."""
import httpx
from unittest.mock import patch


def _understood(**filters):
    """An /api/v1/ask response with the given filters set."""
    names = ["registration", "manufacturer", "model", "operator", "owner", "status"]
    return {
        "question": "Emirates A380s",
        "model": "qwen3",
        "elapsed_ms": 1200,
        "filters": {name: filters.get(name) for name in names},
    }


class TestAskOnSearchPage:
    """Tests for the ask box on the search page."""

    def test_ask_searches_with_the_model_filters(self, client, mock_api_client, sample_search_results):
        """Test the model's filters drive the search and are shown to the reader."""
        mock_api_client.ask.return_value = _understood(operator="Emirates", model="A380")
        mock_api_client.search_aircraft.return_value = sample_search_results

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/search?ask=Emirates+A380s")

        assert response.status_code == 200
        kwargs = mock_api_client.search_aircraft.call_args.kwargs
        assert kwargs["operator"] == "Emirates"
        assert kwargs["model"] == "A380"
        assert kwargs["manufacturer"] is None
        assert "operator: Emirates" in response.text

    def test_ask_failure_shows_an_error_and_skips_the_search(self, client, mock_api_client):
        """Test a failed model call is reported rather than searching everything."""
        mock_api_client.ask.side_effect = Exception("model unavailable")

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/search?ask=anything")

        assert response.status_code == 200
        assert "could not answer" in response.text
        mock_api_client.search_aircraft.assert_not_called()

    def test_ask_without_a_model_says_it_is_switched_off(self, client, mock_api_client):
        """Test a 503 from the API reads as 'switched off', not as a model failure."""
        request = httpx.Request("POST", "http://api/api/v1/ask")
        mock_api_client.ask.side_effect = httpx.HTTPStatusError(
            "503", request=request, response=httpx.Response(503, request=request)
        )

        with patch("app.routers.pages.api_client", mock_api_client):
            response = client.get("/search?ask=anything")

        assert "switched off" in response.text
        mock_api_client.search_aircraft.assert_not_called()

    def test_question_replaces_the_form_filters(self, client, mock_api_client, sample_search_results):
        """Test filters already in the URL are dropped in favour of the model's."""
        mock_api_client.ask.return_value = _understood(model="A380")
        mock_api_client.search_aircraft.return_value = sample_search_results

        with patch("app.routers.pages.api_client", mock_api_client):
            client.get("/search?ask=A380s&manufacturer=Boeing&icao24=abc123")

        kwargs = mock_api_client.search_aircraft.call_args.kwargs
        assert kwargs["model"] == "A380"
        assert kwargs["manufacturer"] is None
        assert kwargs["icao24"] is None
