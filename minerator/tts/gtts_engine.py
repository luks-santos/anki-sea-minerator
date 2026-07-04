from __future__ import annotations

import io

from gtts import gTTS


class GttsTTS:
    def __init__(self, lang: str = "en") -> None:
        self._lang = lang

    def synthesize(self, text: str) -> bytes:
        buffer = io.BytesIO()
        gTTS(text, lang=self._lang).write_to_fp(buffer)
        return buffer.getvalue()
