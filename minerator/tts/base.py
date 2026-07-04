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
        return GttsTTS()
    raise ValueError(f"unknown TTS engine: {name}")
