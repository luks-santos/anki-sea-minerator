import json

import httpx
import pytest

from seaminerator.core.ai.gemini_rest import GeminiError, GeminiRestConnector

PAYLOAD = {
    "words": [
        {
            "expression": "give up",
            "explanation": "stop trying",
            "translations": ["Desistir"],
            "grammar_class": "Phrasal Verb",
            "sentences": [{"text": "Never give up.", "highlight": "give up"}],
        }
    ]
}


def make_connector(handler, model="gemini-2.5-flash"):
    return GeminiRestConnector(
        api_key="secret", model=model, transport=httpx.MockTransport(handler)
    )


def ok(payload):
    return httpx.Response(
        200,
        json={"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]},
    )


def test_mine_parses_response_into_word_blocks():
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["key"] = request.headers.get("x-goog-api-key")
        captured["body"] = json.loads(request.content)
        return ok(PAYLOAD)

    words = make_connector(handler).mine(["give up"], prompt="RULES")

    assert words[0].expression == "give up"
    assert words[0].sentences[0].highlight == "give up"
    assert captured["key"] == "secret"
    assert captured["url"].endswith("/v1beta/models/gemini-2.5-flash:generateContent")


def test_mine_sends_prompt_word_list_and_json_mime_type():
    captured = {}

    def handler(request):
        captured.update(json.loads(request.content))
        return ok(PAYLOAD)

    make_connector(handler).mine(["give up", "overwhelming"], prompt="RULES")

    text = captured["contents"][0]["parts"][0]["text"]
    assert text == "RULES\n\nList of the day:\ngive up\noverwhelming"
    assert captured["generationConfig"]["responseMimeType"] == "application/json"


def test_invalid_key_raises_readable_error():
    def handler(request):
        return httpx.Response(401, json={"error": {"message": "API key not valid"}})

    with pytest.raises(GeminiError, match="API key"):
        make_connector(handler).mine(["give up"], prompt="RULES")


def test_quota_exceeded_raises_readable_error():
    def handler(request):
        return httpx.Response(429, json={"error": {"message": "quota"}})

    with pytest.raises(GeminiError, match="[Qq]uota"):
        make_connector(handler).mine(["give up"], prompt="RULES")


def test_non_json_body_raises_readable_error():
    def handler(request):
        return httpx.Response(200, content=b"not json")

    with pytest.raises(GeminiError, match="unexpected response"):
        make_connector(handler).mine(["give up"], prompt="RULES")


def test_missing_candidates_raises_readable_error():
    def handler(request):
        return httpx.Response(200, json={})

    with pytest.raises(GeminiError, match="unexpected response"):
        make_connector(handler).mine(["give up"], prompt="RULES")


def test_model_text_that_is_not_json_raises_readable_error():
    def handler(request):
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": "sorry"}]}}]}
        )

    with pytest.raises(GeminiError, match="unexpected response"):
        make_connector(handler).mine(["give up"], prompt="RULES")


def test_network_failure_raises_readable_error():
    def handler(request):
        raise httpx.ConnectError("no route to host")

    with pytest.raises(GeminiError, match="[Cc]onnect"):
        make_connector(handler).mine(["give up"], prompt="RULES")
