from __future__ import annotations

import json

import httpx

from ..models import WordBlock, parse_mining_response

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT = 120.0


class GeminiError(Exception):
    pass


class GeminiRestConnector:
    def __init__(self, api_key: str, model: str, transport=None) -> None:
        self._api_key = api_key
        self._model = model
        self._client = httpx.Client(transport=transport, timeout=TIMEOUT)

    def mine(self, words: list[str], prompt: str) -> list[WordBlock]:
        contents = f"{prompt}\n\nList of the day:\n" + "\n".join(words)
        body = {
            "contents": [{"parts": [{"text": contents}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        url = f"{BASE_URL}/{self._model}:generateContent"

        try:
            response = self._client.post(
                url, json=body, headers={"x-goog-api-key": self._api_key}
            )
        except httpx.HTTPError as exc:
            raise GeminiError(f"could not connect to the Gemini API: {exc}") from exc

        self._raise_for_status(response)

        try:
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise GeminiError(
                f"the Gemini API returned an unexpected response: {exc}"
            ) from exc

        try:
            return parse_mining_response(json.loads(text))
        except (ValueError, TypeError) as exc:
            raise GeminiError(
                f"the model returned an unexpected response: {exc}"
            ) from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        detail = ""
        try:
            detail = response.json().get("error", {}).get("message", "")
        except ValueError:
            detail = response.text[:200]
        if response.status_code in (401, 403):
            raise GeminiError(f"invalid or unauthorized API key: {detail}")
        if response.status_code == 429:
            raise GeminiError(f"Gemini API quota exceeded: {detail}")
        raise GeminiError(f"Gemini API error {response.status_code}: {detail}")
