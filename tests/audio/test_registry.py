import pytest

from seaminerator.core.audio.gemini import GeminiRecorder
from seaminerator.core.audio.google import GoogleRecorder
from seaminerator.core.audio.options import GEMINI_KEY_MESSAGE
from seaminerator.core.audio.registry import build_recorder
from seaminerator.core.config import (
    AudioSettings,
    Config,
    ConfigError,
    ProviderSettings,
    default_providers,
)


def encode(wav):
    return b"MP3"


def test_the_system_voice_needs_no_recorder():
    assert build_recorder(Config(), encode) is None


def test_google_records_with_the_chosen_accent():
    cfg = Config(audio=AudioSettings(source="google", google_accent="ie"))

    recorder = build_recorder(cfg, encode)

    assert isinstance(recorder, GoogleRecorder)
    assert recorder.voice == "ie"


def test_gemini_uses_the_gemini_provider_key_and_the_chosen_voice():
    providers = default_providers()
    base_url = providers["gemini"].base_url
    providers["gemini"] = ProviderSettings("g-key", "gemini-2.5-flash", base_url)
    cfg = Config(
        provider="openai",
        providers=providers,
        audio=AudioSettings(source="gemini", gemini_voice="Puck"),
    )

    recorder = build_recorder(cfg, encode)

    assert isinstance(recorder, GeminiRecorder)
    assert recorder.voice == "Puck"


def test_gemini_without_a_key_is_a_config_error():
    with pytest.raises(ConfigError) as caught:
        build_recorder(Config(audio=AudioSettings(source="gemini")), encode)

    assert str(caught.value) == GEMINI_KEY_MESSAGE
