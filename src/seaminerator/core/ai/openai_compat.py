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
from .schema import to_openai_strict


class OpenAICompatProvider:
    """OpenAI's chat completions protocol.

    Also spoken by OpenRouter, Groq and the local servers (Ollama, LM
    Studio), so `openai` and `local` both use this adapter with a different
    `base_url`. `unsupported_hint` is appended to a 400 from the mining call,
    where a server that can't do `json_schema` outputs rejects the request.
    """

    def __init__(
        self,
        name: str,
        api_key: str | None,
        model: str,
        base_url: str,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 120.0,
        unsupported_hint: str | None = None,
    ) -> None:
        self.name = name
        self._unsupported_hint = unsupported_hint
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.Client(transport=transport, timeout=timeout)

    def mine(self, request: MiningRequest) -> dict:
        body = {
            "model": self._model,
            "messages": [{"role": "user", "content": request.text}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "mining",
                    "strict": True,
                    "schema": to_openai_strict(request.schema),
                },
            },
        }
        try:
            data = request_json(
                self._client,
                "POST",
                f"{self._base_url}/chat/completions",
                provider=self.name,
                base_url=self._base_url,
                headers=self._headers,
                body=body,
            )
        except AIError as exc:
            if self._unsupported_hint and "API error 400" in str(exc):
                raise AIError(f"{exc}; {self._unsupported_hint}") from exc
            raise
        try:
            choice = data["choices"][0]
            message = choice["message"]
            refusal = message.get("refusal")
            finish = choice.get("finish_reason")
            content = message.get("content")
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise AIError(OUTSIDE_FORMAT_MESSAGE) from exc
        if refusal:
            raise AIError(f"the model refused the request: {refusal}")
        if finish == "content_filter":
            raise AIError(blocked_message(finish))
        if finish == "length":
            raise AIError(TRUNCATED_MESSAGE)
        if not isinstance(content, str):
            raise AIError(OUTSIDE_FORMAT_MESSAGE)
        return parse_json_object(content)

    def list_models(self) -> list[str]:
        data = request_json(
            self._client,
            "GET",
            f"{self._base_url}/models",
            provider=self.name,
            base_url=self._base_url,
            headers=self._headers,
        )
        try:
            return [model["id"] for model in data["data"]]
        except (KeyError, TypeError) as exc:
            raise AIError(OUTSIDE_FORMAT_MESSAGE) from exc
