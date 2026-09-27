import json

import httpx

from seaminerator.core.ai.base import MiningRequest
from seaminerator.core.ai.gemini import GeminiProvider
from seaminerator.core.ai.schema import mining_schema

BASE = "https://generativelanguage.googleapis.com/v1beta"


def capture(response):
    seen = {}

    def handler(request):
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-goog-api-key")
        seen["body"] = json.loads(request.content) if request.content else None
        return response

    return seen, httpx.MockTransport(handler)


def ok():
    return httpx.Response(
        200, json={"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}
    )


def test_mine_posts_the_prompt_and_the_neutral_schema():
    seen, transport = capture(ok())
    request = MiningRequest(text="RULES", schema=mining_schema())

    GeminiProvider("secret", "gemini-2.5-flash", BASE, transport).mine(request)

    assert seen["url"] == f"{BASE}/models/gemini-2.5-flash:generateContent"
    assert seen["key"] == "secret"
    assert seen["body"]["contents"] == [{"parts": [{"text": "RULES"}]}]
    config = seen["body"]["generationConfig"]
    assert config["responseMimeType"] == "application/json"
    assert config["responseJsonSchema"] == mining_schema()


def test_list_models_asks_for_a_large_page():
    seen, transport = capture(httpx.Response(200, json={"models": []}))

    GeminiProvider("secret", "m", BASE, transport).list_models()

    assert seen["method"] == "GET"
    assert seen["url"] == f"{BASE}/models?pageSize=1000"
