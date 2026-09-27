from __future__ import annotations

import httpx

from .base import (
    OUTSIDE_FORMAT_MESSAGE,
    TRUNCATED_MESSAGE,
    AIError,
    MiningRequest,
    parse_json_object,
)
from .http import request_json


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
        try:
            candidate = data["candidates"][0]
            truncated = candidate.get("finishReason") == "MAX_TOKENS"
            text = candidate["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise AIError(OUTSIDE_FORMAT_MESSAGE) from exc
        if truncated:
            raise AIError(TRUNCATED_MESSAGE)
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
