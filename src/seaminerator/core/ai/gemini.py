from __future__ import annotations

import httpx

from .base import (
    OUTSIDE_FORMAT_MESSAGE,
    TRUNCATED_MESSAGE,
    AIError,
    MiningRequest,
    blocked_message,
    parse_json_object,
)
from .http import request_json

_BLOCKED_FINISH_REASONS = frozenset(
    {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"}
)


class GeminiProvider:
    name = "Gemini"

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
        self._headers = {"x-goog-api-key": api_key}
        self._client = httpx.Client(transport=transport, timeout=timeout)

    def mine(self, request: MiningRequest) -> dict:
        # Gemini accepts standard JSON Schema in `responseJsonSchema`
        # (verified 2026-09-27), so the neutral schema goes out unchanged.
        body = {
            "contents": [{"parts": [{"text": request.text}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": request.schema,
            },
        }
        data = request_json(
            self._client,
            "POST",
            f"{self._base_url}/models/{self._model}:generateContent",
            provider=self.name,
            base_url=self._base_url,
            headers=self._headers,
            body=body,
        )
        # Check why generation stopped before reading the text: a blocked
        # prompt has no candidates, and a truncated or blocked answer may have
        # no parts at all.
        try:
            block_reason = (data.get("promptFeedback") or {}).get("blockReason")
        except (TypeError, AttributeError) as exc:
            raise AIError(OUTSIDE_FORMAT_MESSAGE) from exc
        if block_reason:
            raise AIError(blocked_message(block_reason))
        try:
            candidate = data["candidates"][0]
            finish = candidate.get("finishReason")
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise AIError(OUTSIDE_FORMAT_MESSAGE) from exc
        if finish == "MAX_TOKENS":
            raise AIError(TRUNCATED_MESSAGE)
        if finish in _BLOCKED_FINISH_REASONS:
            raise AIError(blocked_message(finish))
        try:
            text = candidate["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIError(OUTSIDE_FORMAT_MESSAGE) from exc
        return parse_json_object(text)

    def list_models(self) -> list[str]:
        data = request_json(
            self._client,
            "GET",
            f"{self._base_url}/models?pageSize=1000",
            provider=self.name,
            base_url=self._base_url,
            headers=self._headers,
        )
        try:
            return [
                model["name"].removeprefix("models/")
                for model in data["models"]
                if "generateContent" in model.get("supportedGenerationMethods", [])
            ]
        except (KeyError, TypeError, AttributeError) as exc:
            raise AIError(OUTSIDE_FORMAT_MESSAGE) from exc
