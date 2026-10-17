import base64
import io
import json
import wave

import httpx
import pytest

from seaminerator.core.audio.base import AudioError
from seaminerator.core.audio.gemini import GeminiRecorder, pcm_to_wav, request_body

BASE = "https://generativelanguage.googleapis.com/v1beta"
MODEL = "gemini-3.8-flash-lite-tts"


def audio_response(data: bytes, mime: str) -> httpx.Response:
    part = {"inlineData": {"mimeType": mime, "data": base64.b64encode(data).decode()}}
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [part]}}]})


def recorder(response):
    seen = {"encoded": []}

    def handler(request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-goog-api-key")
        seen["body"] = json.loads(request.content)
        return response

    def encode(wav: bytes) -> bytes:
        seen["encoded"].append(wav)
        return b"MP3"

    return seen, GeminiRecorder(
        "key-1", MODEL, "Kore", encode, BASE, transport=httpx.MockTransport(handler)
    )


def test_record_sends_the_text_voice_and_audio_modality():
    seen, rec = recorder(audio_response(pcm_to_wav(b"\0\0" * 10, 24000), "audio/wav"))

    rec.record("Hello there.")

    assert seen["url"] == f"{BASE}/models/{MODEL}:generateContent"
    assert seen["key"] == "key-1"
    assert seen["body"] == request_body("Hello there.", "Kore")
    config = seen["body"]["generationConfig"]
    assert config["responseModalities"] == ["AUDIO"]
    assert config["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"] == {
        "voiceName": "Kore"
    }


def test_a_wav_answer_goes_to_the_encoder_as_is():
    # What gemini-3.8-flash-lite-tts answered with on 2026-10-11.
    wav = pcm_to_wav(b"\x01\x00" * 50, 24000)
    seen, rec = recorder(audio_response(wav, "audio/wav"))

    assert rec.record("Hi.") == b"MP3"
    assert seen["encoded"] == [wav]


def test_a_raw_pcm_answer_is_wrapped_at_its_sample_rate():
    seen, rec = recorder(
        audio_response(b"\0\0" * 160, "audio/L16;codec=pcm;rate=16000")
    )

    rec.record("Hi.")

    with wave.open(io.BytesIO(seen["encoded"][0])) as wav:
        assert (wav.getnchannels(), wav.getsampwidth()) == (1, 2)
        assert (wav.getframerate(), wav.getnframes()) == (16000, 160)


def test_an_answer_without_audio_is_a_per_card_failure():
    response = httpx.Response(
        200, json={"candidates": [{"content": {"parts": [{"text": "no"}]}}]}
    )
    _seen, rec = recorder(response)

    with pytest.raises(AudioError, match="no audio") as caught:
        rec.record("Hi.")

    assert caught.value.source_down is False


def test_an_unknown_audio_format_means_the_source_is_down():
    _seen, rec = recorder(audio_response(b"OggS....", "audio/ogg"))

    with pytest.raises(AudioError, match="audio/ogg") as caught:
        rec.record("Hi.")

    assert caught.value.source_down is True


@pytest.mark.parametrize(
    ("status", "words"), [(401, "API key"), (403, "API key"), (429, "quota")]
)
def test_key_and_quota_errors_mean_the_source_is_down(status, words):
    _seen, rec = recorder(httpx.Response(status, json={"error": {"message": "x"}}))

    with pytest.raises(AudioError, match=words) as caught:
        rec.record("Hi.")

    assert caught.value.source_down is True


def test_an_encoder_failure_propagates():
    def handler(request):
        return audio_response(pcm_to_wav(b"\0\0", 24000), "audio/wav")

    def encode(wav):
        raise AudioError("Gemini audio needs LAME", source_down=True)

    rec = GeminiRecorder(
        "k", MODEL, "Kore", encode, BASE, transport=httpx.MockTransport(handler)
    )

    with pytest.raises(AudioError, match="LAME"):
        rec.record("Hi.")


class ClosableTransport(httpx.MockTransport):
    closed = False

    def close(self):
        self.closed = True


def test_close_releases_the_connections():
    transport = ClosableTransport(lambda request: httpx.Response(200))
    rec = GeminiRecorder("k", MODEL, "Kore", lambda wav: b"", BASE, transport=transport)

    rec.close()

    assert transport.closed is True
