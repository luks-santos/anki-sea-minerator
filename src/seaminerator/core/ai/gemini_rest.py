from __future__ import annotations

import json
from collections.abc import Sequence

import httpx

from ..models import WordBlock, parse_mining_response
from ..prompt import tagging_instructions
from ..tags import CLASS_TAGS

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT = 120.0

_STRING = {"type": "STRING"}

# Gemini's `responseSchema` (OpenAPI subset, uppercase types). The `enum` on
# `class_tag` is what keeps the model from inventing near-duplicate classes
# like "noun-phrase"; topics stay free-form strings, normalized on parse.
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "words": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "expression": _STRING,
                    "explanation": _STRING,
                    "translations": {"type": "ARRAY", "items": _STRING},
                    "class_tag": {"type": "STRING", "enum": list(CLASS_TAGS)},
                    "sentences": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "text": _STRING,
                                "highlight": _STRING,
                                "note": _STRING,
                                "topics": {"type": "ARRAY", "items": _STRING},
                            },
                            "required": ["text", "highlight", "topics"],
                            "propertyOrdering": ["text", "highlight", "note", "topics"],
                        },
                    },
                },
                # Without `propertyOrdering` the REST API may generate fields
                # alphabetically. `class_tag` goes last so the class is chosen
                # after the sentences exist, as the prompt's rules require.
                "propertyOrdering": [
                    "expression",
                    "explanation",
                    "translations",
                    "sentences",
                    "class_tag",
                ],
                "required": [
                    "expression",
                    "explanation",
                    "translations",
                    "class_tag",
                    "sentences",
                ],
            },
        }
    },
    "required": ["words"],
}


class GeminiError(Exception):
    pass


class GeminiRestConnector:
    def __init__(self, api_key: str, model: str, transport=None) -> None:
        self._api_key = api_key
        self._model = model
        self._client = httpx.Client(transport=transport, timeout=TIMEOUT)

    def mine(
        self, words: list[str], prompt: str, topics: Sequence[str] = ()
    ) -> list[WordBlock]:
        contents = (
            f"{prompt}\n\n{tagging_instructions(list(topics))}\n\nList of the day:\n"
            + "\n".join(words)
        )
        body = {
            "contents": [{"parts": [{"text": contents}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": RESPONSE_SCHEMA,
            },
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
            return parse_mining_response(json.loads(text), topics)
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
