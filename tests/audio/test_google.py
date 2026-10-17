import base64
import json
import urllib.parse

import httpx
import pytest

from seaminerator.core.audio.base import AudioError
from seaminerator.core.audio.google import GoogleRecorder, parse_audio, request_body

MP3 = b"\xff\xf3fake-mp3"


def batch_response(data: bytes = MP3) -> str:
    # The shape Google answered with on 2026-10-11: the audio sits as base64
    # inside a JSON string inside the "wrb.fr" line.
    b64 = base64.b64encode(data).decode()
    return (
        ")]}'\n\n123\n"
        + '[["wrb.fr","jQ1olc","[\\"'
        + b64
        + '\\"]",null,null,null,"generic"]]\n'
        + '58\n[["di",29],["af.httprm",29,"1",3]]\n'
    )


def capture(response):
    seen = {}

    def handler(request):
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["type"] = request.headers.get("content-type")
        seen["body"] = request.content.decode()
        return response

    return seen, httpx.MockTransport(handler)


def test_record_posts_to_the_accent_domain():
    seen, transport = capture(httpx.Response(200, text=batch_response()))

    GoogleRecorder("co.uk", transport=transport).record("Hello there.")

    assert seen["method"] == "POST"
    assert seen["url"] == (
        "https://translate.google.co.uk/_/TranslateWebserverUi/data/batchexecute"
    )
    assert seen["type"] == "application/x-www-form-urlencoded;charset=utf-8"


def test_request_body_carries_the_text_in_the_rpc_payload():
    text = 'Don\'t stop: 100% & "more" +1 é'

    outer = json.loads(urllib.parse.parse_qs(request_body(text))["f.req"][0])

    assert outer[0][0][0] == "jQ1olc"
    assert outer[0][0][3] == "generic"
    assert json.loads(outer[0][0][1]) == [text, "en", None, "null"]


def test_record_returns_the_decoded_mp3():
    _seen, transport = capture(httpx.Response(200, text=batch_response()))

    assert GoogleRecorder("us", transport=transport).record("Hello.") == MP3


def test_the_recorder_reports_its_source_and_accent():
    recorder = GoogleRecorder("com.au")
    assert (recorder.source, recorder.voice) == ("google", "com.au")


def test_no_audio_in_the_response_is_a_per_card_failure():
    with pytest.raises(AudioError) as caught:
        parse_audio(')]}\'\n\n[["wrb.fr","jQ1olc",null,null,null,"generic"]]\n')

    assert caught.value.source_down is False


def test_long_text_fails_without_sending_a_request():
    seen, transport = capture(httpx.Response(200, text=batch_response()))

    with pytest.raises(AudioError, match="100 characters") as caught:
        GoogleRecorder("us", transport=transport).record("x" * 101)

    assert caught.value.source_down is False
    assert seen == {}


@pytest.mark.parametrize("status", [403, 429, 503, 400])
def test_http_errors_mean_the_source_is_down(status):
    _seen, transport = capture(httpx.Response(status, text="nope"))

    with pytest.raises(AudioError, match="Google Translate") as caught:
        GoogleRecorder("us", transport=transport).record("Hello.")

    assert caught.value.source_down is True


def test_a_connection_error_means_the_source_is_down():
    def handler(request):
        raise httpx.ConnectError("no route", request=request)

    with pytest.raises(AudioError, match="could not connect") as caught:
        GoogleRecorder("us", transport=httpx.MockTransport(handler)).record("Hello.")

    assert caught.value.source_down is True


class ClosableTransport(httpx.MockTransport):
    closed = False

    def close(self):
        self.closed = True


def test_close_releases_the_connections():
    transport = ClosableTransport(lambda request: httpx.Response(200))
    recorder = GoogleRecorder("us", transport=transport)

    recorder.close()

    assert transport.closed is True
