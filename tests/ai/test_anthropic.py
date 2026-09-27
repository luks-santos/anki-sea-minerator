import json

import httpx
import pytest

from seaminerator.core.ai.anthropic import AnthropicProvider
from seaminerator.core.ai.base import AIError, MiningRequest
from seaminerator.core.ai.schema import mining_schema

REQUEST = MiningRequest(text="RULES", schema=mining_schema())


def capture(response):
    seen = {}

    def handler(request):
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-api-key")
        seen["version"] = request.headers.get("anthropic-version")
        seen["body"] = json.loads(request.content) if request.content else None
        return response

    return seen, httpx.MockTransport(handler)


def tool_message(content):
    return httpx.Response(200, json={"content": content, "stop_reason": "tool_use"})


def provider(transport):
    return AnthropicProvider(
        "secret", "claude-haiku-4-5-20251001", "https://api.anthropic.com", transport
    )


def test_mine_forces_the_schema_as_a_tool():
    seen, transport = capture(
        tool_message([{"type": "tool_use", "name": "record_mining", "input": {}}])
    )

    provider(transport).mine(REQUEST)

    assert seen["url"] == "https://api.anthropic.com/v1/messages"
    assert seen["key"] == "secret"
    assert seen["version"] == "2023-06-01"
    body = seen["body"]
    assert body["model"] == "claude-haiku-4-5-20251001"
    assert body["max_tokens"] == 16384
    assert body["messages"] == [{"role": "user", "content": "RULES"}]
    assert body["tools"][0]["name"] == "record_mining"
    assert body["tools"][0]["input_schema"] == mining_schema()
    assert body["tool_choice"] == {"type": "tool", "name": "record_mining"}


def test_mine_skips_text_blocks_before_the_tool_call():
    _, transport = capture(
        tool_message(
            [
                {"type": "text", "text": "Here you go."},
                {"type": "tool_use", "name": "record_mining", "input": {"words": []}},
            ]
        )
    )

    assert provider(transport).mine(REQUEST) == {"words": []}


def test_list_models_gets_the_models_endpoint():
    seen, transport = capture(httpx.Response(200, json={"data": []}))

    assert provider(transport).list_models() == []
    assert seen["method"] == "GET"
    assert seen["url"] == "https://api.anthropic.com/v1/models?limit=1000"


def test_refusal_stop_reason_is_reported_as_refused():
    _, transport = capture(
        httpx.Response(200, json={"content": [], "stop_reason": "refusal"})
    )
    with pytest.raises(AIError, match=r"refused or blocked the request \(refusal\)"):
        provider(transport).mine(REQUEST)
