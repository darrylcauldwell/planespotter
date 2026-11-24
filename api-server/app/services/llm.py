import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
import httpx
from pydantic import BaseModel
from app.config import settings
from app.metrics import LLM_FIRST_TOKEN, LLM_LATENCY, LLM_TOKENS


class LLMError(Exception):
    """The language model could not be reached or gave no usable answer."""


class LLMNotConfigured(LLMError):
    """No language model endpoint is configured."""


def answer_schema(output_type: type[BaseModel]) -> dict:
    """The JSON schema the model answers in: every key required, null where a field allows it.

    Required keys make a small model consider each field in turn. With optional keys in a fixed
    order it writes the field the question mentions first and cannot go back to one it skipped:
    "Ryanair 737s" lost its model filter that way.
    """
    schema = output_type.model_json_schema()
    schema["required"] = list(schema["properties"])
    return schema


@dataclass(frozen=True)
class Completion[T: BaseModel]:
    """A validated answer, the model that gave it, and how long it took."""

    output: T
    model: str
    seconds: float


class LLMClient:
    """Chat completions over the plain OpenAI REST API.

    Plain HTTP rather than an SDK, so the same requests reach llama.cpp, Private AI Services or
    OpenAI by changing only the base URL, and the image needs no new package.
    """

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    async def complete[T: BaseModel](
        self, feature: str, messages: list[dict], output_type: type[T], max_tokens: int = 256
    ) -> Completion[T]:
        """Ask for an answer in the shape of `output_type`, and validate it."""
        body = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": feature, "schema": answer_schema(output_type)},
            },
        }

        start = time.perf_counter()
        try:
            async with self._http() as client:
                response = await client.post(self._url(), json=body, headers=self._headers())
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMError(f"Request to the language model failed: {e!r}") from e
        seconds = time.perf_counter() - start
        LLM_LATENCY.labels(feature=feature).observe(seconds)

        # Anything short of a complete answer in the schema is the model's failure, not the
        # caller's: a gateway's HTML error page, an empty choice list, or JSON cut off at
        # max_tokens.
        try:
            data = response.json()
            choice = data["choices"][0]
            output = output_type.model_validate_json(choice["message"]["content"])
        except (KeyError, IndexError, TypeError, AttributeError, ValueError) as e:
            raise LLMError(f"Unusable answer from the language model: {e!r}") from e

        self._count_tokens(feature, data.get("usage"))
        return Completion(output=output, model=data.get("model") or settings.llm_model, seconds=seconds)

    async def stream(
        self, feature: str, messages: list[dict], max_tokens: int = 256, temperature: float = 0.3
    ) -> AsyncIterator[str]:
        """Yield the model's reply as it is written.

        Nothing is requested until the first piece is awaited, so a missing or failing model
        raises there, before any text has been passed on.
        """
        body = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        start = time.perf_counter()
        first_piece = None
        usage = None
        try:
            async with self._http() as client:
                async with client.stream("POST", self._url(), json=body, headers=self._headers()) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line.removeprefix("data:").strip()
                        if data == "[DONE]":
                            break
                        chunk = json.loads(data)
                        if "error" in chunk:
                            raise LLMError(f"The language model stopped: {chunk['error']}")
                        usage = chunk.get("usage") or usage
                        for choice in chunk.get("choices") or []:
                            piece = (choice.get("delta") or {}).get("content")
                            if piece:
                                if first_piece is None:
                                    first_piece = time.perf_counter()
                                    LLM_FIRST_TOKEN.labels(feature=feature).observe(first_piece - start)
                                yield piece
        except httpx.HTTPError as e:
            raise LLMError(f"Request to the language model failed: {e!r}") from e
        except (TypeError, AttributeError, ValueError) as e:
            raise LLMError(f"Unusable answer from the language model: {e!r}") from e

        LLM_LATENCY.labels(feature=feature).observe(time.perf_counter() - start)
        self._count_tokens(feature, usage)

    def _http(self) -> httpx.AsyncClient:
        if not settings.llm_base_url:
            raise LLMNotConfigured("No language model is configured")
        return httpx.AsyncClient(timeout=settings.llm_timeout, transport=self._transport)

    @staticmethod
    def _url() -> str:
        return f"{settings.llm_base_url.rstrip('/')}/chat/completions"

    @staticmethod
    def _headers() -> dict:
        return {"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else {}

    @staticmethod
    def _count_tokens(feature: str, usage: dict | None) -> None:
        usage = usage or {}
        LLM_TOKENS.labels(feature=feature, kind="prompt").inc(usage.get("prompt_tokens", 0))
        LLM_TOKENS.labels(feature=feature, kind="completion").inc(usage.get("completion_tokens", 0))


llm_client = LLMClient()
