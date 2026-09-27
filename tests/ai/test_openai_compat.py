import json

import httpx
import pytest

from seaminerator.core.ai.base import AIError, MiningRequest
from seaminerator.core.ai.openai_compat import OpenAICompatProvider
from seaminerator.core.ai.schema import mining_schema, to_openai_strict

REQUEST = MiningRequest(text="RULES", schema=mining_schema())


def capture(response):
    seen = {}

    def handler(request):
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content) if request.content else None
        return response

    return seen, httpx.MockTransport(handler)


def completion(message, finish_reason="stop"):
    return httpx.Response(
        200, json={"choices": [{"message": message, "finish_reason": finish_reason}]}
    )


def provider(transport, api_key="secret", base_url="https://api.openai.com/v1"):
    return OpenAICompatProvider("OpenAI", api_key, "gpt-test", base_url, transport)


def test_mine_posts_chat_completion_with_a_strict_json_schema():
    seen, transport = capture(completion({"content": "{}"}))

    provider(transport).mine(REQUEST)

    assert seen["url"] == "https://api.openai.com/v1/chat/completions"
    assert seen["auth"] == "Bearer secret"
    body = seen["body"]
    assert body["model"] == "gpt-test"
    assert body["messages"] == [{"role": "user", "content": "RULES"}]
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "mining",
            "strict": True,
            "schema": to_openai_strict(mining_schema()),
        },
    }


def test_keyless_local_provider_sends_no_authorization_header():
    seen, transport = capture(completion({"content": "{}"}))

    provider(transport, api_key=None, base_url="http://localhost:11434/v1").mine(
        REQUEST
    )

    assert seen["auth"] is None
    assert seen["url"] == "http://localhost:11434/v1/chat/completions"


def test_trailing_slash_in_base_url_is_tolerated():
    seen, transport = capture(completion({"content": "{}"}))

    provider(transport, base_url="https://api.openai.com/v1/").mine(REQUEST)

    assert seen["url"] == "https://api.openai.com/v1/chat/completions"


def test_refusal_raises_with_the_models_reason():
    _, transport = capture(completion({"content": None, "refusal": "not allowed"}))

    with pytest.raises(AIError, match="the model refused the request: not allowed"):
        provider(transport).mine(REQUEST)


def test_list_models_gets_the_models_endpoint():
    seen, transport = capture(httpx.Response(200, json={"data": []}))

    assert provider(transport).list_models() == []
    assert seen["method"] == "GET"
    assert seen["url"] == "https://api.openai.com/v1/models"
