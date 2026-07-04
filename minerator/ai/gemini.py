from __future__ import annotations

import json

from minerator.models import WordBlock, parse_mining_response


class GeminiConnector:
    def __init__(self, api_key: str, model: str, client=None) -> None:
        self._model = model
        if client is None:
            from google import genai

            client = genai.Client(api_key=api_key)
        self._client = client

    def mine(self, words: list[str], prompt: str) -> list[WordBlock]:
        contents = f"{prompt}\n\nList of the day:\n" + "\n".join(words)
        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config={"response_mime_type": "application/json"},
        )
        return parse_mining_response(json.loads(response.text))
