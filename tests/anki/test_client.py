import json

import httpx
import pytest

from minerator.anki.client import AnkiClient, AnkiConnectError


def make_client(handler):
    transport = httpx.MockTransport(handler)
    return AnkiClient(transport=transport)


def test_deck_names_returns_result():
    def handler(request):
        payload = json.loads(request.content)
        assert payload["action"] == "deckNames"
        assert payload["version"] == 6
        return httpx.Response(200, json={"result": ["Default", "English"], "error": None})

    assert make_client(handler).deck_names() == ["Default", "English"]


def test_add_note_sends_note_structure_and_returns_id():
    captured = {}

    def handler(request):
        payload = json.loads(request.content)
        captured.update(payload)
        return httpx.Response(200, json={"result": 1512, "error": None})

    note_id = make_client(handler).add_note(
        deck="English", model="Básico",
        fields={"Frente": "front", "Verso": "back"}, tags=["mined"],
    )
    assert note_id == 1512
    note = captured["params"]["note"]
    assert note["deckName"] == "English"
    assert note["modelName"] == "Básico"
    assert note["fields"] == {"Frente": "front", "Verso": "back"}
    assert note["tags"] == ["mined"]


def test_error_response_raises():
    def handler(request):
        return httpx.Response(200, json={"result": None, "error": "deck not found"})

    with pytest.raises(AnkiConnectError, match="deck not found"):
        make_client(handler).add_note(deck="X", model="Básico", fields={})


def test_ping_true_on_version():
    def handler(request):
        return httpx.Response(200, json={"result": 6, "error": None})

    assert make_client(handler).ping() is True


def test_add_note_raises_when_result_is_null_without_error():
    def handler(request):
        return httpx.Response(200, json={"result": None, "error": None})

    with pytest.raises(AnkiConnectError):
        make_client(handler).add_note(deck="English", model="Básico", fields={})


def test_ping_false_on_non_json_response():
    def handler(request):
        return httpx.Response(200, content=b"not json")

    assert make_client(handler).ping() is False


def test_ping_false_on_non_dict_json_response():
    def handler(request):
        return httpx.Response(200, json=["Default", "English"])

    assert make_client(handler).ping() is False
