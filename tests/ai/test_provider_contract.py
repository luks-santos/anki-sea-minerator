import json
from collections.abc import Callable
from dataclasses import dataclass

import httpx
import pytest

from seaminerator.core.ai.base import AIError, MiningRequest
from seaminerator.core.ai.gemini import GeminiProvider
from seaminerator.core.ai.openai_compat import OpenAICompatProvider
from seaminerator.core.ai.schema import mining_schema

PAYLOAD = {
    "words": [
        {
            "expression": "give up",
            "explanation": "stop trying",
            "translations": ["Desistir"],
            "sentences": [
                {"text": "Never give up.", "highlight": "give up", "topics": []}
            ],
            "class_tag": "phrasal-verb",
        }
    ]
}
REQUEST = MiningRequest(text="RULES", schema=mining_schema())


@dataclass
class ProviderCase:
    id: str
    build: Callable[[httpx.MockTransport], object]
    ok: Callable[[dict], httpx.Response]
    truncated: Callable[[], httpx.Response]
    models: Callable[[], httpx.Response]
    expected_models: list[str]


def gemini_case() -> ProviderCase:
    return ProviderCase(
        id="gemini",
        build=lambda transport: GeminiProvider(
            api_key="secret",
            model="gemini-2.5-flash",
            base_url="https://generativelanguage.googleapis.com/v1beta",
            transport=transport,
        ),
        ok=lambda payload: httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": [{"text": json.dumps(payload)}]},
                        "finishReason": "STOP",
                    }
                ]
            },
        ),
        truncated=lambda: httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": [{"text": '{"words": ['}]},
                        "finishReason": "MAX_TOKENS",
                    }
                ]
            },
        ),
        models=lambda: httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "models/gemini-2.5-flash",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/text-embedding-004",
                        "supportedGenerationMethods": ["embedContent"],
                    },
                ]
            },
        ),
        expected_models=["gemini-2.5-flash"],
    )


def openai_case() -> ProviderCase:
    def completion(content, finish_reason="stop"):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": finish_reason,
                    }
                ]
            },
        )

    return ProviderCase(
        id="openai",
        build=lambda transport: OpenAICompatProvider(
            name="OpenAI",
            api_key="secret",
            model="gpt-test",
            base_url="https://api.openai.com/v1",
            transport=transport,
        ),
        ok=lambda payload: completion(json.dumps(payload)),
        truncated=lambda: completion('{"words": [', finish_reason="length"),
        models=lambda: httpx.Response(
            200, json={"data": [{"id": "gpt-a"}, {"id": "gpt-b"}]}
        ),
        expected_models=["gpt-a", "gpt-b"],
    )


CASES = [gemini_case(), openai_case()]


@pytest.fixture(params=CASES, ids=lambda case: case.id)
def case(request):
    return request.param


def provider_for(case, handler):
    return case.build(httpx.MockTransport(handler))


def test_mine_returns_the_json_object(case):
    provider = provider_for(case, lambda request: case.ok(PAYLOAD))
    assert provider.mine(REQUEST) == PAYLOAD


def test_truncated_response_raises(case):
    provider = provider_for(case, lambda request: case.truncated())
    with pytest.raises(AIError, match="cut off by the model's output limit"):
        provider.mine(REQUEST)


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (401, "invalid or unauthorized API key"),
        (403, "invalid or unauthorized API key"),
        (429, "quota or rate limit exceeded"),
        (500, "API error 500"),
    ],
)
def test_http_errors_raise_readable_errors(case, status, message):
    provider = provider_for(
        case, lambda request: httpx.Response(status, json={"error": {"message": "x"}})
    )
    with pytest.raises(AIError, match=message):
        provider.mine(REQUEST)


def test_connection_error_raises(case):
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(AIError, match="could not connect"):
        provider_for(case, handler).mine(REQUEST)


def test_success_body_without_the_expected_shape_raises(case):
    provider = provider_for(case, lambda request: httpx.Response(200, json={}))
    with pytest.raises(AIError, match="outside the expected format"):
        provider.mine(REQUEST)


def test_list_models_parses_the_model_ids(case):
    provider = provider_for(case, lambda request: case.models())
    assert provider.list_models() == case.expected_models


def test_list_models_with_an_unexpected_body_raises(case):
    provider = provider_for(case, lambda request: httpx.Response(200, json=[]))
    with pytest.raises(AIError, match="outside the expected format"):
        provider.list_models()
