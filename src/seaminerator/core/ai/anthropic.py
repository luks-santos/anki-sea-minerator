from __future__ import annotations

import httpx

from .base import OUTSIDE_FORMAT_MESSAGE, TRUNCATED_MESSAGE, AIError, MiningRequest
from .http import request_json

ANTHROPIC_VERSION = "2023-06-01"
MAX_TOKENS = 8192
TOOL_NAME = "record_mining"


class AnthropicProvider:
    """Claude, with the response schema as a tool the model must call.

    Forcing a single tool (`tool_choice`) is the robust way to get JSON
    that matches a schema from the Messages API: the tool's `input` is
    that JSON, already parsed.
    """

    name = "Anthropic"

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._headers = {"x-api-key": api_key, "anthropic-version": ANTHROPIC_VERSION}
        self._client = httpx.Client(transport=transport, timeout=timeout)

    def mine(self, request: MiningRequest) -> dict:
        body = {
            "model": self._model,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": request.text}],
            "tools": [
                {
                    "name": TOOL_NAME,
                    "description": "Record the mined vocabulary.",
                    "input_schema": request.schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": TOOL_NAME},
        }
        data = request_json(
            self._client,
            "POST",
            f"{self._base_url}/v1/messages",
            provider=self.name,
            base_url=self._base_url,
            headers=self._headers,
            body=body,
        )
        try:
            truncated = data.get("stop_reason") == "max_tokens"
            blocks = data["content"]
            tool_input = next(
                (b["input"] for b in blocks if b.get("type") == "tool_use"), None
            )
        except (KeyError, TypeError, AttributeError) as exc:
            raise AIError(OUTSIDE_FORMAT_MESSAGE) from exc
        if truncated:
            raise AIError(TRUNCATED_MESSAGE)
        if not isinstance(tool_input, dict):
            raise AIError(OUTSIDE_FORMAT_MESSAGE)
        return tool_input

    def list_models(self) -> list[str]:
        data = request_json(
            self._client,
            "GET",
            f"{self._base_url}/v1/models?limit=1000",
            provider=self.name,
            base_url=self._base_url,
            headers=self._headers,
        )
        try:
            return [model["id"] for model in data["data"]]
        except (KeyError, TypeError) as exc:
            raise AIError(OUTSIDE_FORMAT_MESSAGE) from exc
