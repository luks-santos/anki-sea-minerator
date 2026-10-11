import json
from pathlib import Path

import pytest

from seaminerator.addon_config import (
    config_from_dict,
    config_to_dict,
    display_config,
    with_native_language,
)
from seaminerator.core.config import (
    AudioSettings,
    Config,
    ConfigError,
    ProviderSettings,
)

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


def test_a_stored_awesometts_voice_is_dropped():
    # Saved by a version that listed it; the note type then loses it on the
    # next mining or import.
    data = shipped()
    data["tts_voices"] = ["AwesomeTTS"]
    assert config_from_dict(data).tts_voices == ()


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


def test_reads_the_native_language_and_edited_prompts():
    data = shipped()
    data["native_language"] = "ja"
    data["prompts"] = {"ja": "日本語で説明して", "es": "Explica en español"}

    cfg = config_from_dict(data)

    assert cfg.native_language == "ja"
    assert cfg.prompts == {"ja": "日本語で説明して", "es": "Explica en español"}


def test_config_to_dict_round_trips_the_language_and_prompts():
    data = shipped()
    data["native_language"] = "zh-TW"
    data["prompts"] = {"zh-TW": "用繁體中文解釋 {braces}"}
    cfg = config_from_dict(data)

    # Through real JSON, as Anki stores it.
    stored = json.loads(json.dumps(config_to_dict(cfg)))

    assert config_from_dict(stored) == cfg


def test_missing_language_settings_use_the_defaults():
    # Configs saved before this version lack both keys.
    data = shipped()
    del data["native_language"], data["prompts"]

    cfg = config_from_dict(data)

    assert cfg.native_language == ""
    assert cfg.prompts == {}


@pytest.mark.parametrize("code", ["en", "pt_BR", "xx", 5, None])
def test_unknown_native_language_is_a_config_error(code):
    data = shipped()
    data["native_language"] = code
    with pytest.raises(ConfigError, match="native language"):
        config_from_dict(data)


@pytest.mark.parametrize("prompts", ["text", ["a"], None, {"xx": "text"}, {"es": 5}])
def test_malformed_prompts_are_a_config_error(prompts):
    data = shipped()
    data["prompts"] = prompts
    with pytest.raises(ConfigError, match="prompt"):
        config_from_dict(data)


def test_blank_prompt_entries_are_dropped():
    data = shipped()
    data["prompts"] = {"es": "  \n", "fr": "Explique en français"}
    assert config_from_dict(data).prompts == {"fr": "Explique en français"}


def test_display_config_keeps_the_language_and_prompts_of_a_broken_config():
    data = shipped()
    data["provider"] = "nope"
    data["native_language"] = "es"
    data["prompts"] = {"es": "Mi prompt"}

    cfg = display_config(data)

    assert cfg.native_language == "es"
    assert cfg.prompts == {"es": "Mi prompt"}


def test_display_config_drops_an_unknown_language_of_a_broken_config():
    data = shipped()
    data["native_language"] = "xx"
    data["prompts"] = {"es": 5}
    data["default_deck"] = "Grammar"

    cfg = display_config(data)

    assert cfg.native_language == ""
    assert cfg.prompts == {}
    assert cfg.default_deck == "Grammar"


def test_display_config_keeps_the_providers_when_only_the_language_is_unreadable():
    # Settings would otherwise open with blank keys, and Save would wipe them.
    data = shipped()
    data["providers"]["anthropic"]["api_key"] = "kept"
    data["provider"] = "anthropic"
    data["native_language"] = "xx"

    cfg = display_config(data)

    assert cfg.provider == "anthropic"
    assert cfg.providers["anthropic"].api_key == "kept"
    assert cfg.native_language == ""


def test_display_config_keeps_every_readable_prompt():
    data = shipped()
    data["prompts"] = {"es": "Mi prompt", "en": "x", "fr": 5}

    cfg = display_config(data)

    assert cfg.prompts == {"es": "Mi prompt"}


def test_display_config_keeps_the_readable_prompts_of_a_broken_provider():
    data = shipped()
    data["provider"] = "nope"
    data["prompts"] = {"es": "Mi prompt", "en": "x"}

    assert display_config(data).prompts == {"es": "Mi prompt"}


def test_with_native_language_changes_only_that_key():
    # A stored config that doesn't parse: the choice must still be saved
    # without touching anything else.
    data = {"provider": "nope", "default_deck": "Grammar"}

    updated = with_native_language(data, "es")

    assert updated == {
        "provider": "nope",
        "default_deck": "Grammar",
        "native_language": "es",
    }
    assert "native_language" not in data


def test_a_stale_prompt_path_is_ignored():
    # Configs saved before this version still carry it.
    data = shipped()
    data["prompt_path"] = "C:/old/prompt.txt"

    assert config_from_dict(data) == Config()
    assert "prompt_path" not in config_to_dict(Config())


def test_reads_a_recorded_audio_source_and_its_settings():
    data = shipped()
    data["audio"] = {
        "source": "gemini",
        "google": {"accent": "co.uk"},
        "gemini": {"voice": "Puck", "model": "gemini-x-tts"},
    }

    assert config_from_dict(data).audio == AudioSettings(
        source="gemini",
        google_accent="co.uk",
        gemini_voice="Puck",
        gemini_model="gemini-x-tts",
    )


def test_missing_audio_settings_use_the_defaults():
    data = shipped()
    del data["audio"]
    assert config_from_dict(data).audio == AudioSettings()

    data["audio"] = {"source": "google"}
    assert config_from_dict(data).audio == AudioSettings(source="google")


@pytest.mark.parametrize(
    "audio",
    [
        "google",
        {"source": "edge"},
        {"source": 5},
        {"google": {"accent": "com"}},
        {"google": {"accent": ["us"]}},
        {"google": "us"},
        {"gemini": {"voice": ""}},
        {"gemini": {"model": 5}},
    ],
)
def test_malformed_audio_settings_are_a_config_error(audio):
    data = shipped()
    data["audio"] = audio
    with pytest.raises(ConfigError, match="audio|accent|Gemini"):
        config_from_dict(data)


def test_config_to_dict_round_trips_the_audio_settings():
    data = shipped()
    data["audio"] = {"source": "google", "google": {"accent": "ie"}}
    cfg = config_from_dict(data)

    assert config_from_dict(json.loads(json.dumps(config_to_dict(cfg)))) == cfg


def test_display_config_keeps_the_audio_settings_of_a_broken_provider():
    data = shipped()
    data["provider"] = "nope"
    data["audio"] = {"source": "google", "google": {"accent": "ca"}}

    assert display_config(data).audio == AudioSettings(
        source="google", google_accent="ca"
    )


def test_display_config_drops_only_unreadable_audio_settings():
    data = shipped()
    data["providers"]["gemini"]["api_key"] = "kept"
    data["audio"] = {"source": "edge"}

    cfg = display_config(data)

    assert cfg.audio == AudioSettings()
    assert cfg.providers["gemini"].api_key == "kept"
