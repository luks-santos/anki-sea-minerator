import dataclasses

import pytest

from seaminerator.core.config import PROVIDERS, Config, ProviderSettings, voice_names


def test_default_config_uses_gemini_without_a_key():
    cfg = Config()
    assert cfg.provider == "gemini"
    assert cfg.providers["gemini"] == ProviderSettings(
        api_key=None,
        model="gemini-2.5-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta",
    )
    assert cfg.tts_lang == "en_US"
    assert cfg.highlight_color == "#2563eb"
    assert cfg.tts_voices == ()
    assert cfg.tts_speed == 1.0


def test_providers_table_matches_the_spec():
    assert list(PROVIDERS) == ["gemini", "openai", "anthropic", "local"]
    assert PROVIDERS["local"].needs_key is False
    assert PROVIDERS["local"].timeout == 300.0
    assert PROVIDERS["openai"].base_url_editable is True
    assert PROVIDERS["anthropic"].base_url_editable is False
    assert PROVIDERS["anthropic"].default.model == "claude-haiku-4-5-20251001"
    assert PROVIDERS["local"].default.base_url == "http://localhost:11434/v1"


def test_config_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        Config().provider = "openai"  # type: ignore[misc]


def test_voice_names_trims_and_drops_blank_entries():
    assert voice_names([" Microsoft_Zira", "", "  ", "Microsoft_David "]) == (
        "Microsoft_Zira",
        "Microsoft_David",
    )


def test_voice_names_spells_spaces_the_way_anki_names_voices():
    assert voice_names(["Microsoft  Zira"]) == ("Microsoft_Zira",)
