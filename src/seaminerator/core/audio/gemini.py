from __future__ import annotations

import base64
import binascii
import io
import re
import wave
from collections.abc import Callable
from typing import Any

import httpx

from .base import AudioError
from .http import post

SOURCE = "Gemini"
_RATE = re.compile(r"rate=(\d+)")
_DEFAULT_RATE = 24000


def request_body(text: str, voice: str) -> dict:
    return {
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}
            },
        },
    }


def pcm_to_wav(pcm: bytes, rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm)
    return buffer.getvalue()


def wav_from_response(data: Any) -> bytes:
    # 3.8 TTS models answer with a complete WAV; older ones sent raw 16-bit
    # PCM labeled audio/L16 with its rate in the mime type.
    try:
        inline = data["candidates"][0]["content"]["parts"][0]["inlineData"]
        mime = str(inline.get("mimeType", ""))
        audio = base64.b64decode(inline["data"])
    except (
        KeyError,
        IndexError,
        TypeError,
        AttributeError,
        binascii.Error,
        ValueError,
    ) as exc:
        raise AudioError(f"{SOURCE} returned no audio", source_down=False) from exc
    if audio[:4] == b"RIFF":
        return audio
    if mime.lower().startswith(("audio/l16", "audio/pcm")):
        match = _RATE.search(mime)
        return pcm_to_wav(audio, int(match.group(1)) if match else _DEFAULT_RATE)
    raise AudioError(
        f"{SOURCE} returned audio as {mime or 'an unknown format'}", source_down=True
    )


class GeminiRecorder:
    source = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        voice: str,
        encode_mp3: Callable[[bytes], bytes],
        base_url: str,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.voice = voice
        self._url = f"{base_url.rstrip('/')}/models/{model}:generateContent"
        self._headers = {"x-goog-api-key": api_key}
        # Injected so core never runs LAME or imports aqt; the GUI passes
        # one that uses the LAME Anki ships.
        self._encode_mp3 = encode_mp3
        self._client = httpx.Client(transport=transport, timeout=timeout)

    def record(self, text: str) -> bytes:
        response = post(
            self._client,
            self._url,
            source=SOURCE,
            key_hint=True,
            headers=self._headers,
            json=request_body(text, self.voice),
        )
        try:
            data = response.json()
        except ValueError as exc:
            raise AudioError(f"{SOURCE} returned no audio", source_down=False) from exc
        return self._encode_mp3(wav_from_response(data))
