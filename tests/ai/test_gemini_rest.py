import json

import httpx
import pytest

from seaminerator.core.ai.gemini_rest import GeminiError, GeminiRestConnector
from seaminerator.core.prompt import tagging_instructions
from seaminerator.core.tags import CLASS_TAGS

PAYLOAD = {
    "words": [
        {
            "expression": "give up",
            "explanation": "stop trying",
            "translations": ["Desistir"],
            "class_tag": "phrasal-verb",
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


def test_mine_sends_prompt_tagging_rules_word_list_and_json_mime_type():
    captured = {}

    def handler(request):
        captured.update(json.loads(request.content))
        return ok(PAYLOAD)

    make_connector(handler).mine(
        ["give up", "overwhelming"], prompt="RULES", topics=["past-simple"]
    )

    text = captured["contents"][0]["parts"][0]["text"]
    assert text == (
        "RULES\n\n"
        + tagging_instructions(["past-simple"])
        + "\n\nList of the day:\ngive up\noverwhelming"
    )
    assert captured["generationConfig"]["responseMimeType"] == "application/json"


def test_mine_without_topics_says_there_are_none():
    captured = {}

    def handler(request):
        captured.update(json.loads(request.content))
        return ok(PAYLOAD)

    make_connector(handler).mine(["give up"], prompt="RULES")

    text = captured["contents"][0]["parts"][0]["text"]
    assert "There are no existing topic tags yet." in text


def test_mine_constrains_class_tag_with_a_response_schema():
    captured = {}

    def handler(request):
        captured.update(json.loads(request.content))
        return ok(PAYLOAD)

    make_connector(handler).mine(["give up"], prompt="RULES")

    schema = captured["generationConfig"]["responseSchema"]
    word = schema["properties"]["words"]["items"]
    assert word["properties"]["class_tag"] == {
        "type": "STRING",
        "enum": list(CLASS_TAGS),
    }
    assert "class_tag" in word["required"]
    sentence = word["properties"]["sentences"]["items"]
    assert sentence["properties"]["topics"] == {
        "type": "ARRAY",
        "items": {"type": "STRING"},
    }
    assert "topics" in sentence["required"]


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


def test_server_error_raises_readable_error():
    def handler(request):
        return httpx.Response(500, json={"error": {"message": "internal"}})

    with pytest.raises(GeminiError, match="Gemini API error 500"):
        make_connector(handler).mine(["give up"], prompt="RULES")


def test_mine_maps_topics_back_to_the_collection_spelling():
    payload = json.loads(json.dumps(PAYLOAD))
    payload["words"][0]["sentences"][0]["topics"] = ["verb-to-be"]

    words = make_connector(lambda request: ok(payload)).mine(
        ["give up"], prompt="RULES", topics=["Verb_To_Be"]
    )

    assert words[0].sentences[0].topics == ["Verb_To_Be"]
