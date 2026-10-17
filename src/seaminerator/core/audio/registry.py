from __future__ import annotations

from collections.abc import Callable

from ..config import Config, ConfigError
from .base import Recorder
from .gemini import GeminiRecorder
from .google import GoogleRecorder
from .options import GEMINI_KEY_MESSAGE


def build_recorders(
    cfg: Config, encode_mp3: Callable[[bytes], bytes]
) -> list[Recorder]:
    """The chain of sources to record with, in order; empty for the system voice.

    Gemini is backed up by Google Translate, so a quota or outage on Gemini
    still yields recordings; whatever no source records uses the system voice.
    """
    audio = cfg.audio
    if audio.source == "google":
        return [GoogleRecorder(audio.google_accent)]
    if audio.source == "gemini":
        # The Gemini provider's key and URL, whichever provider mines.
        gemini = cfg.providers["gemini"]
        if not gemini.api_key:
            raise ConfigError(GEMINI_KEY_MESSAGE)
        first = GeminiRecorder(
            gemini.api_key,
            audio.gemini_model,
            audio.gemini_voice,
            encode_mp3,
            gemini.base_url,
        )
        return [first, GoogleRecorder(audio.google_accent)]
    return []
