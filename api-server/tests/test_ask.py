"""Tests for asking Planespotter in plain English."""
import json
import httpx
import pytest
from pydantic import ValidationError
from unittest.mock import AsyncMock, patch

from app.config import settings
from app.schemas.ask import SearchFilters
from app.services.ask import interpret_question
from app.services.llm import Completion, LLMClient, LLMError, LLMNotConfigured


def _chat_reply(content: str, model: str = "qwen3-4b") -> dict:
    """An OpenAI chat completion carrying `content` as the answer."""
    return {
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 600, "completion_tokens": 20},
    }


@pytest.fixture
def llm_configured():
    """Point the client at a model server, with an API key."""
    with patch.object(settings, "llm_base_url", "http://llm:8080/v1"), \
         patch.object(settings, "llm_model", "configured-name"), \
         patch.object(settings, "llm_api_key", "secret-token"):
        yield


class TestAskEndpoint:
    """Tests for POST /api/v1/ask."""

    def test_ask_returns_filters_model_and_time(self, client):
        """Test the model's filters come back with the model's name and the time it took."""
        answer = Completion(
            output=SearchFilters(operator="Emirates", model="A380", status="airborne"),
            model="qwen3-4b",
            seconds=1.25,
        )
        with patch("app.routers.ask.interpret_question", AsyncMock(return_value=answer)):
            response = client.post("/api/v1/ask", json={"question": "Emirates A380s flying now"})

        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["operator"] == "Emirates"
        assert data["filters"]["registration"] is None
        assert data["model"] == "qwen3-4b"
        assert data["elapsed_ms"] == 1250

    def test_ask_without_model_configured(self, client):
        """Test the endpoint reports 503 when no model URL is set."""
        with patch.object(settings, "llm_base_url", None):
            response = client.post("/api/v1/ask", json={"question": "anything"})

        assert response.status_code == 503

    def test_ask_when_model_fails(self, client):
        """Test a failed model call is reported as a bad gateway."""
        with patch("app.routers.ask.interpret_question", AsyncMock(side_effect=LLMError("refused"))):
            response = client.post("/api/v1/ask", json={"question": "anything"})

        assert response.status_code == 502

    def test_ask_rejects_empty_question(self, client):
        """Test an empty question is rejected before reaching the model."""
        response = client.post("/api/v1/ask", json={"question": ""})
        assert response.status_code == 422


class TestSearchFilters:
    """Tests for validating the model's answer."""

    def test_blank_values_mean_no_filter(self):
        """Test empty and whitespace values become None and others are trimmed."""
        filters = SearchFilters.model_validate_json(
            '{"manufacturer": "", "model": " A380 ", "owner": "  ", "operator": "Emirates"}'
        )
        assert filters.model == "A380"
        assert filters.operator == "Emirates"
        assert filters.manufacturer is None
        assert filters.owner is None

    def test_unknown_status_is_rejected(self):
        """Test a status the search cannot apply is refused rather than passed on."""
        with pytest.raises(ValidationError):
            SearchFilters(status="flying")

    def test_schema_bounds_every_string(self):
        """Test every free-text filter has a length limit for the model's grammar."""
        properties = SearchFilters.model_json_schema()["properties"]
        for name, prop in properties.items():
            if name != "status":
                assert prop["anyOf"][0]["maxLength"] > 0, name


class TestInterpretQuestion:
    """Tests for the prompt sent to the model."""

    async def test_prompt_has_examples_and_ends_with_the_question(self):
        """Test the examples answer with every key, as the model must, and the question comes last."""
        answer = Completion(output=SearchFilters(model="A380"), model="m", seconds=0.1)
        with patch("app.services.ask.llm_client.complete", AsyncMock(return_value=answer)) as complete:
            result = await interpret_question("Emirates A380s")

        assert result is answer
        messages = complete.call_args.args[1]
        assert messages[0]["role"] == "system"
        assert messages[-1] == {"role": "user", "content": "Emirates A380s"}
        example_reply = json.loads(messages[2]["content"])
        assert example_reply == {
            "registration": None,
            "manufacturer": None,
            "model": "A380",
            "operator": "Emirates",
            "owner": None,
            "status": "airborne",
        }


class TestLLMClient:
    """Tests for the OpenAI-compatible client, against a fake model server."""

    @staticmethod
    def _client(handler) -> LLMClient:
        return LLMClient(transport=httpx.MockTransport(handler))

    async def test_sends_an_openai_request_and_validates_the_answer(self, llm_configured):
        """Test the request shape, the auth header, and the parsed answer."""
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["auth"] = request.headers.get("authorization")
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json=_chat_reply('{"model": "A380", "operator": "Emirates"}'))

        answer = await self._client(handler).complete(
            "ask", [{"role": "user", "content": "q"}], SearchFilters
        )

        assert seen["url"] == "http://llm:8080/v1/chat/completions"
        assert seen["auth"] == "Bearer secret-token"
        assert seen["body"]["model"] == "configured-name"
        schema = seen["body"]["response_format"]["json_schema"]["schema"]
        assert schema["required"] == list(SearchFilters.model_fields)
        assert answer.output == SearchFilters(model="A380", operator="Emirates")
        assert answer.model == "qwen3-4b"
        assert answer.seconds >= 0

    async def test_no_auth_header_without_a_key(self, llm_configured):
        """Test a server without authentication gets no Authorization header."""
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["auth"] = request.headers.get("authorization")
            return httpx.Response(200, json=_chat_reply("{}"))

        with patch.object(settings, "llm_api_key", None):
            await self._client(handler).complete("ask", [], SearchFilters)

        assert seen["auth"] is None

    @pytest.mark.parametrize(
        "response",
        [
            httpx.Response(200, json=_chat_reply('{"model": "A38')),
            httpx.Response(200, json=_chat_reply('{"status": "flying"}')),
            httpx.Response(200, json={"choices": []}),
            httpx.Response(200, json={"choices": [{"message": {"content": None}}]}),
            httpx.Response(200, text="<html>gateway error</html>"),
            httpx.Response(500, text="model crashed"),
        ],
        ids=["cut-off-json", "invalid-status", "no-choices", "null-content", "html-page", "server-error"],
    )
    async def test_unusable_answers_raise_llm_error(self, llm_configured, response):
        """Test every way a model server can fail surfaces as LLMError."""
        with pytest.raises(LLMError):
            await self._client(lambda request: response).complete("ask", [], SearchFilters)

    async def test_unreachable_server_raises_llm_error(self, llm_configured):
        """Test a connection failure surfaces as LLMError."""
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        with pytest.raises(LLMError):
            await self._client(handler).complete("ask", [], SearchFilters)

    async def test_unconfigured_client_raises_not_configured(self):
        """Test a missing base URL is reported distinctly from a failure."""
        with patch.object(settings, "llm_base_url", None), pytest.raises(LLMNotConfigured):
            await LLMClient().complete("ask", [], SearchFilters)
