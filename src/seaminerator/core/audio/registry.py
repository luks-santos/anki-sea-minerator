from __future__ import annotations

from collections.abc import Callable

from ..config import Config, ConfigError
from .base import Recorder
from .gemini import GeminiRecorder
from .google import GoogleRecorder
from .options import GEMINI_KEY_MESSAGE


def build_recorder(
    cfg: Config, encode_mp3: Callable[[bytes], bytes]
) -> Recorder | None:
    audio = cfg.audio
    if audio.source == "google":
        return GoogleRecorder(audio.google_accent)
    if audio.source == "gemini":
        # The Gemini provider's key and URL, whichever provider mines.
        gemini = cfg.providers["gemini"]
        if not gemini.api_key:
            raise ConfigError(GEMINI_KEY_MESSAGE)
        return GeminiRecorder(
            gemini.api_key,
            audio.gemini_model,
            audio.gemini_voice,
            encode_mp3,
            gemini.base_url,
        )
    return None
