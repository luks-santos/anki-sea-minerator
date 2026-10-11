from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from .audio.options import GEMINI_TTS_MODEL


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class ProviderSettings:
    api_key: str | None
    model: str
    base_url: str


@dataclass(frozen=True)
class ProviderInfo:
    display_name: str
    needs_key: bool
    base_url_editable: bool
    timeout: float
    default: ProviderSettings


PROVIDERS: dict[str, ProviderInfo] = {
    "gemini": ProviderInfo(
        "Gemini",
        needs_key=True,
        base_url_editable=False,
        timeout=120.0,
        default=ProviderSettings(
            None,
            "gemini-2.5-flash",
            "https://generativelanguage.googleapis.com/v1beta",
        ),
    ),
    "openai": ProviderInfo(
        "OpenAI & compatible",
        needs_key=True,
        base_url_editable=True,
        timeout=120.0,
        default=ProviderSettings(None, "", "https://api.openai.com/v1"),
    ),
    "anthropic": ProviderInfo(
        "Anthropic",
        needs_key=True,
        base_url_editable=False,
        timeout=120.0,
        default=ProviderSettings(
            None, "claude-haiku-4-5-20251001", "https://api.anthropic.com"
        ),
    ),
    "local": ProviderInfo(
        "Local (Ollama, LM Studio)",
        needs_key=False,
        base_url_editable=True,
        # Local models on a CPU can take minutes for a full list.
        timeout=300.0,
        default=ProviderSettings(None, "", "http://localhost:11434/v1"),
    ),
}


# Bounds for Anki's {{tts}} speed= option; 1.0 is the voice's normal pace.
TTS_SPEED_MIN = 0.5
TTS_SPEED_MAX = 2.0


# Voices other add-ons register with Anki. AwesomeTTS's speaks only for
# languages set up in that add-on and doesn't exist on phones, so a card
# asking for it gets an error instead of audio.
UNSUPPORTED_VOICES = frozenset({"AwesomeTTS"})


def voice_names(names: Iterable[str]) -> tuple[str, ...]:
    # Anki names voices with underscores ("Microsoft_Zira"), and a space
    # would end the {{tts}} tag's voices= option.
    spelled = ("_".join(name.split()) for name in names if name.strip())
    return tuple(name for name in spelled if name not in UNSUPPORTED_VOICES)


def default_providers() -> dict[str, ProviderSettings]:
    return {provider_id: info.default for provider_id, info in PROVIDERS.items()}


@dataclass(frozen=True)
class AudioSettings:
    # "system" speaks with the device's voices through {{tts}}; "google" and
    # "gemini" record an MP3 per card, falling back to {{tts}} on failure.
    source: str = "system"
    google_accent: str = "us"
    gemini_voice: str = "Kore"
    gemini_model: str = GEMINI_TTS_MODEL


@dataclass(frozen=True)
class Config:
    provider: str = "gemini"
    providers: dict[str, ProviderSettings] = field(default_factory=default_providers)
    default_deck: str = ""
    tts_lang: str = "en_US"
    # In order of preference: {{tts}} uses the first one the device has.
    tts_voices: tuple[str, ...] = ()
    tts_speed: float = 1.0
    highlight_color: str = "#2563eb"
    # "" until the user picks one; mining refuses to start without it.
    native_language: str = ""
    # Edited prompt bodies by language code; a language without an entry
    # uses its default prompt.
    prompts: dict[str, str] = field(default_factory=dict)
    audio: AudioSettings = field(default_factory=AudioSettings)
