from __future__ import annotations

import base64
import binascii
import json
import re
import urllib.parse

import httpx

from .base import AudioError
from .http import post

SOURCE = "Google Translate"
# Google Translate's limit per request; gTTS splits longer text, we fall
# back to the system voice instead (mined sentences are 20-50 characters).
MAX_CHARS = 100

# The endpoint gTTS has used since v2.2.0 (2020); unofficial.
_URL = "https://translate.google.{accent}/_/TranslateWebserverUi/data/batchexecute"
_HEADERS = {
    "Referer": "http://translate.google.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36"
    ),
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
}
_RPC = "jQ1olc"
_AUDIO = re.compile(r'jQ1olc","\[\\"(.*)\\"]')


def request_body(text: str) -> str:
    inner = json.dumps([text, "en", None, "null"], separators=(",", ":"))
    outer = json.dumps([[[_RPC, inner, None, "generic"]]], separators=(",", ":"))
    return "f.req=" + urllib.parse.quote(outer) + "&"


def parse_audio(body: str) -> bytes:
    for line in body.splitlines():
        if _RPC not in line:
            continue
        match = _AUDIO.search(line)
        if match:
            try:
                return base64.b64decode(match.group(1))
            except (binascii.Error, ValueError):
                break
    raise AudioError(f"{SOURCE} returned no audio", source_down=False)


class GoogleRecorder:
    source = "google"
    name = SOURCE

    def __init__(
        self,
        accent: str,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.voice = accent
        self._url = _URL.format(accent=accent)
        self._client = httpx.Client(transport=transport, timeout=timeout)

    def record(self, text: str) -> bytes:
        if len(text) > MAX_CHARS:
            raise AudioError(
                f"longer than {MAX_CHARS} characters, the {SOURCE} limit",
                source_down=False,
            )
        response = post(
            self._client,
            self._url,
            source=SOURCE,
            headers=_HEADERS,
            content=request_body(text),
        )
        return parse_audio(response.text)

    def close(self) -> None:
        self._client.close()
