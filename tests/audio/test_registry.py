import pytest

from seaminerator.core.audio.gemini import GeminiRecorder
from seaminerator.core.audio.google import GoogleRecorder
from seaminerator.core.audio.options import GEMINI_KEY_MESSAGE
from seaminerator.core.audio.registry import build_recorders
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
    assert build_recorders(Config(), encode) == []


def test_google_records_with_the_chosen_accent_and_no_backup():
    cfg = Config(audio=AudioSettings(source="google", google_accent="ie"))

    recorders = build_recorders(cfg, encode)

    assert len(recorders) == 1
    assert isinstance(recorders[0], GoogleRecorder)
    assert recorders[0].voice == "ie"


def test_gemini_is_backed_up_by_google_with_the_chosen_accent():
    providers = default_providers()
    base_url = providers["gemini"].base_url
    providers["gemini"] = ProviderSettings("g-key", "gemini-2.5-flash", base_url)
    cfg = Config(
        provider="openai",
        providers=providers,
        audio=AudioSettings(source="gemini", gemini_voice="Puck", google_accent="ca"),
    )

    first, backup = build_recorders(cfg, encode)

    assert isinstance(first, GeminiRecorder)
    assert first.voice == "Puck"
    assert isinstance(backup, GoogleRecorder)
    assert backup.voice == "ca"


def test_recorders_have_display_names():
    assert GoogleRecorder("us").name == "Google Translate"
    assert GeminiRecorder("k", "m", "Kore", encode, "https://x").name == "Gemini"


def test_gemini_without_a_key_is_a_config_error():
    with pytest.raises(ConfigError) as caught:
        build_recorders(Config(audio=AudioSettings(source="gemini")), encode)

    assert str(caught.value) == GEMINI_KEY_MESSAGE
