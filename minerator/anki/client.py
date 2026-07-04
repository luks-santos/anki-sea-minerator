from __future__ import annotations

import httpx


class AnkiConnectError(Exception):
    pass


class AnkiClient:
    def __init__(self, url: str = "http://localhost:8765", transport=None) -> None:
        self._url = url
        self._client = httpx.Client(transport=transport, timeout=30.0)

    def _invoke(self, action: str, **params):
        payload = {"action": action, "version": 6, "params": params}
        try:
            response = self._client.post(self._url, json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise AnkiConnectError(f"AnkiConnect request failed: {exc}") from exc
        if data.get("error") is not None:
            raise AnkiConnectError(str(data["error"]))
        return data.get("result")

    def ping(self) -> bool:
        try:
            return self._invoke("version") == 6
        except AnkiConnectError:
            return False

    def deck_names(self) -> list[str]:
        return list(self._invoke("deckNames"))

    def model_names(self) -> list[str]:
        return list(self._invoke("modelNames"))

    def model_field_names(self, model: str) -> list[str]:
        return list(self._invoke("modelFieldNames", modelName=model))

    def store_media_file(self, filename: str, data_b64: str) -> str:
        self._invoke("storeMediaFile", filename=filename, data=data_b64)
        return filename

    def add_note(
        self, deck: str, model: str, fields: dict, tags: list | None = None
    ) -> int:
        note = {
            "deckName": deck,
            "modelName": model,
            "fields": fields,
            "tags": tags or [],
            "options": {"allowDuplicate": False},
        }
        return int(self._invoke("addNote", note=note))
