from __future__ import annotations

from typing import Protocol

from minerator.tts.edge import EdgeTTS
from minerator.tts.gtts_engine import GttsTTS


class TTSEngine(Protocol):
    def synthesize(self, text: str) -> bytes: ...


def get_engine(name: str, voice: str) -> TTSEngine:
    if name == "edge":
        return EdgeTTS(voice)
    if name == "gtts":
        lang = voice.split("-")[0].lower() if voice else "en"
        return GttsTTS(lang=lang)
    raise ValueError(f"unknown TTS engine: {name}")
