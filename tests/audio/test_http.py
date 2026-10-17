import httpx
import pytest

from seaminerator.core.audio.base import AudioError
from seaminerator.core.audio.http import post

URL = "https://tts.example/speak"


def client(*responses: httpx.Response):
    """A client answering with `responses` in order, and the requests it got."""
    queue = list(responses)
    requests: list[httpx.Request] = []

    def handler(request):
        requests.append(request)
        return queue.pop(0)

    return httpx.Client(transport=httpx.MockTransport(handler)), requests


def gemini_error(status: int, message: str, retry_delay: str | None = None):
    # The shape Gemini documents: google.rpc.Status, with RetryInfo on a 429.
    details = []
    if retry_delay is not None:
        details.append(
            {
                "@type": "type.googleapis.com/google.rpc.RetryInfo",
                "retryDelay": retry_delay,
            }
        )
    error = {"code": status, "message": message, "details": details}
    return httpx.Response(status, json={"error": error})


def test_a_server_error_is_retried_until_it_answers(sleeps):
    http, requests = client(httpx.Response(503), httpx.Response(200, text="ok"))

    response = post(http, URL, source="Gemini")

    assert response.text == "ok"
    assert len(requests) == 2
    assert sleeps == [1.0]


def test_a_rate_limit_waits_as_long_as_retry_after_says(sleeps):
    http, _requests = client(
        httpx.Response(429, headers={"Retry-After": "3"}), httpx.Response(200)
    )

    post(http, URL, source="Google Translate")

    assert sleeps == [3.0]


def test_a_gemini_rate_limit_waits_for_its_retry_delay(sleeps):
    http, _requests = client(
        gemini_error(429, "Rate limit hit.", retry_delay="7.5s"), httpx.Response(200)
    )

    post(http, URL, source="Gemini")

    assert sleeps == [7.5]


def test_a_wait_longer_than_worth_it_stops_without_retrying(sleeps):
    # A spent daily quota: retrying in a few seconds would only fail again.
    http, requests = client(gemini_error(429, "Quota exceeded.", retry_delay="3600s"))

    with pytest.raises(AudioError) as caught:
        post(http, URL, source="Gemini")

    assert caught.value.source_down is True
    assert len(requests) == 1
    assert sleeps == []


def test_a_server_that_stays_down_gets_two_retries_then_stops(sleeps):
    http, requests = client(*[httpx.Response(503)] * 3)

    with pytest.raises(AudioError, match=r"unavailable \(HTTP 503\)") as caught:
        post(http, URL, source="Gemini")

    assert caught.value.source_down is True
    assert len(requests) == 3
    assert sleeps == [1.0, 2.0]


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_a_client_error_is_not_retried(status, sleeps):
    http, requests = client(httpx.Response(status, text="no"))

    with pytest.raises(AudioError):
        post(http, URL, source="Gemini")

    assert len(requests) == 1
    assert sleeps == []


def test_a_refused_key_keeps_the_server_s_message_and_the_hint():
    http, _requests = client(gemini_error(403, "API key not valid. Please pass a key."))

    with pytest.raises(AudioError) as caught:
        post(http, URL, source="Gemini", key_hint=True)

    assert str(caught.value) == (
        "Gemini refused the request (HTTP 403): API key not valid. Please pass a "
        "key; check the API key in Sea Minerator settings"
    )


def test_a_spent_quota_keeps_the_server_s_message():
    http, _requests = client(
        *[gemini_error(429, "You exceeded your current quota.")] * 3
    )

    with pytest.raises(AudioError) as caught:
        post(http, URL, source="Gemini")

    assert str(caught.value) == (
        "Gemini quota or rate limit exceeded (HTTP 429): "
        "You exceeded your current quota"
    )


def test_a_page_instead_of_an_error_message_is_left_out():
    # Google Translate answers a block with an HTML page, not JSON.
    page = httpx.Response(429, text="<html><body>unusual traffic</body></html>")
    http, _requests = client(*[page] * 3)

    with pytest.raises(AudioError) as caught:
        post(http, URL, source="Google Translate")

    assert str(caught.value) == (
        "Google Translate quota or rate limit exceeded (HTTP 429)"
    )
