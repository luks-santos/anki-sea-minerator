import json
from pathlib import Path

import pytest

from seaminerator.addon_config import config_from_dict, config_to_dict
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
