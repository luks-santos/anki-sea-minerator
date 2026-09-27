import json

import httpx
import pytest

from seaminerator.core.ai.base import AIError
from seaminerator.core.ai.http import request_json


def call(handler, method="POST", body=None):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return request_json(
        client,
        method,
        "https://example.test/v1/thing",
        provider="Acme",
        base_url="https://example.test/v1",
        headers={"x-key": "secret"},
        body=body,
    )


def test_returns_the_parsed_json_and_sends_headers_and_body():
    seen = {}

    def handler(request):
        seen["key"] = request.headers.get("x-key")
        seen["body"] = request.content
        return httpx.Response(200, json={"ok": True})

    assert call(handler, body={"a": 1}) == {"ok": True}
    assert seen["key"] == "secret"
    assert json.loads(seen["body"]) == {"a": 1}


def test_get_sends_no_body():
    def handler(request):
        assert request.method == "GET"
        assert request.content == b""
        return httpx.Response(200, json=[])

    assert call(handler, method="GET") == []


@pytest.mark.parametrize("status", [401, 403])
def test_auth_errors_name_the_provider_and_the_settings(status):
    def handler(request):
        return httpx.Response(status, json={"error": {"message": "bad key"}})

    with pytest.raises(AIError, match="invalid or unauthorized API key for Acme"):
        call(handler)


def test_rate_limit_error():
    def handler(request):
        return httpx.Response(429, json={"error": {"message": "slow down"}})

    with pytest.raises(AIError, match="Acme quota or rate limit exceeded: slow down"):
        call(handler)


def test_other_http_errors_carry_status_and_detail():
    def handler(request):
        return httpx.Response(500, json={"error": {"message": "internal"}})

    with pytest.raises(AIError, match="Acme API error 500: internal"):
        call(handler)


def test_error_body_that_is_a_json_list_falls_back_to_raw_text():
    def handler(request):
        return httpx.Response(500, json=["unexpected", "shape"])

    with pytest.raises(AIError, match="Acme API error 500"):
        call(handler)


def test_error_whose_error_field_is_a_string_falls_back_to_raw_text():
    def handler(request):
        return httpx.Response(403, json={"error": "forbidden"})

    with pytest.raises(AIError, match="invalid or unauthorized API key"):
        call(handler)


def test_connection_error_names_the_base_url():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(AIError, match="could not connect to https://example.test/v1"):
        call(handler)


def test_non_json_success_body():
    def handler(request):
        return httpx.Response(200, content=b"<html>")

    with pytest.raises(AIError, match="outside the expected format"):
        call(handler)


def test_timeout_is_not_reported_as_a_connection_problem():
    def handler(request):
        raise httpx.ReadTimeout("slow")

    with pytest.raises(AIError, match="Acme did not answer in time") as info:
        call(handler)
    assert "could not connect" not in str(info.value)
