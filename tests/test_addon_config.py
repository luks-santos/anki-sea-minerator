import json
from pathlib import Path

import pytest

from seaminerator.addon_config import (
    config_from_dict,
    config_to_dict,
    display_config,
)
from seaminerator.core.config import Config, ConfigError, ProviderSettings

SHIPPED = Path(__file__).parent.parent / "src" / "seaminerator" / "config.json"


def shipped():
    return json.loads(SHIPPED.read_text(encoding="utf-8"))


def test_shipped_config_reads_as_the_defaults():
    assert config_from_dict(shipped()) == Config()


def test_reads_the_active_provider_and_its_key():
    data = shipped()
    data["provider"] = "openai"
    data["providers"]["openai"]["api_key"] = "sk-1"
    data["providers"]["openai"]["model"] = "gpt-test"

    cfg = config_from_dict(data)

    assert cfg.provider == "openai"
    assert cfg.providers["openai"] == ProviderSettings(
        "sk-1", "gpt-test", "https://api.openai.com/v1"
    )


@pytest.mark.parametrize("key", ["", "   ", 12345, None])
def test_blank_or_non_string_key_is_missing(key):
    data = shipped()
    data["providers"]["gemini"]["api_key"] = key
    assert config_from_dict(data).providers["gemini"].api_key is None


def test_unknown_top_level_keys_are_ignored():
    data = shipped()
    data["gemini_api_key"] = "old-flat-key"
    assert config_from_dict(data) == Config()


def test_unknown_provider_is_a_config_error():
    data = shipped()
    data["provider"] = "nope"
    with pytest.raises(ConfigError, match="nope"):
        config_from_dict(data)


def test_missing_providers_block_is_a_config_error():
    data = shipped()
    del data["providers"]
    with pytest.raises(ConfigError, match="providers"):
        config_from_dict(data)


def test_missing_provider_entry_is_filled_from_its_defaults():
    # A stored `providers` block replaces the shipped one wholesale (Anki
    # merges only top-level keys), so a provider added in a later version is
    # missing from every existing user's config and must not wipe it.
    data = shipped()
    data["providers"]["gemini"]["api_key"] = "kept"
    del data["providers"]["anthropic"]

    cfg = config_from_dict(data)

    assert cfg.providers["anthropic"] == Config().providers["anthropic"]
    assert cfg.providers["gemini"].api_key == "kept"


def test_malformed_provider_entry_is_a_config_error():
    data = shipped()
    data["providers"]["anthropic"] = "not a block"
    with pytest.raises(ConfigError, match="anthropic"):
        config_from_dict(data)


def test_non_string_model_is_a_config_error():
    data = shipped()
    data["providers"]["gemini"]["model"] = 5
    with pytest.raises(ConfigError, match="gemini"):
        config_from_dict(data)


def test_non_string_top_level_value_is_a_config_error():
    data = shipped()
    data["tts_lang"] = 1
    with pytest.raises(ConfigError, match="tts_lang"):
        config_from_dict(data)


def test_config_to_dict_round_trips():
    data = shipped()
    data["providers"]["anthropic"]["api_key"] = "ak-1"
    cfg = config_from_dict(data)
    assert config_from_dict(config_to_dict(cfg)) == cfg


def test_config_to_dict_writes_a_missing_key_as_blank():
    assert config_to_dict(Config())["providers"]["gemini"]["api_key"] == ""


def test_display_config_keeps_top_level_values_of_a_broken_config():
    data = shipped()
    data["provider"] = "nope"
    data["tts_lang"] = "en_GB"
    data["default_deck"] = "Grammar"

    cfg = display_config(data)

    assert cfg.tts_lang == "en_GB"
    assert cfg.default_deck == "Grammar"
    assert cfg.provider == "gemini"


def test_display_config_ignores_non_string_values_of_a_broken_config():
    cfg = display_config({"tts_lang": 5})
    assert cfg.tts_lang == Config().tts_lang


def test_display_config_reads_a_valid_config_normally():
    data = shipped()
    data["providers"]["gemini"]["api_key"] = "k"
    assert display_config(data) == config_from_dict(data)


def test_reads_the_chosen_voices_and_speed():
    data = shipped()
    data["tts_voices"] = [" Microsoft_Zira", "", "Apple_Samantha"]
    data["tts_speed"] = 0.8

    cfg = config_from_dict(data)

    assert cfg.tts_voices == ("Microsoft_Zira", "Apple_Samantha")
    assert cfg.tts_speed == 0.8


def test_a_whole_number_speed_is_accepted():
    data = shipped()
    data["tts_speed"] = 2
    assert config_from_dict(data).tts_speed == 2.0


def test_missing_voice_settings_use_the_defaults():
    # Configs saved before voices existed lack both keys.
    data = shipped()
    del data["tts_voices"], data["tts_speed"]
    assert config_from_dict(data) == Config()


@pytest.mark.parametrize("voices", ["Microsoft_Zira", ["ok", 5], None])
def test_voices_that_are_not_a_list_of_text_are_a_config_error(voices):
    data = shipped()
    data["tts_voices"] = voices
    with pytest.raises(ConfigError, match="tts_voices"):
        config_from_dict(data)


@pytest.mark.parametrize("speed", ["1.0", True, 0.4, 2.1, None])
def test_speed_outside_the_range_or_not_a_number_is_a_config_error(speed):
    data = shipped()
    data["tts_speed"] = speed
    with pytest.raises(ConfigError, match="tts_speed"):
        config_from_dict(data)


def test_config_to_dict_round_trips_the_voice_settings():
    data = shipped()
    data["tts_voices"] = ["Microsoft_Zira"]
    data["tts_speed"] = 1.5
    cfg = config_from_dict(data)

    written = config_to_dict(cfg)

    assert written["tts_voices"] == ["Microsoft_Zira"]
    assert config_from_dict(written) == cfg


def test_display_config_keeps_the_voice_settings_of_a_broken_config():
    data = shipped()
    data["provider"] = "nope"
    data["tts_voices"] = ["Microsoft_Zira"]
    data["tts_speed"] = 0.7

    cfg = display_config(data)

    assert cfg.tts_voices == ("Microsoft_Zira",)
    assert cfg.tts_speed == 0.7


def test_display_config_drops_invalid_voice_settings_of_a_broken_config():
    cfg = display_config({"tts_voices": "x", "tts_speed": 9})
    assert cfg.tts_voices == ()
    assert cfg.tts_speed == 1.0
