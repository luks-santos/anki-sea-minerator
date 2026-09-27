from seaminerator.core.config import Config, ProviderSettings, default_providers
from seaminerator.core.settings import (
    form_to_config,
    settings_from_form,
    validate,
    visible_fields,
)


def test_fixed_url_providers_hide_the_base_url():
    assert visible_fields("gemini") == {"api_key", "model"}
    assert visible_fields("anthropic") == {"api_key", "model"}


def test_editable_url_providers_show_the_base_url():
    assert visible_fields("openai") == {"api_key", "model", "base_url"}
    assert visible_fields("local") == {"api_key", "model", "base_url"}


def test_settings_from_form_trims_and_blanks_the_key():
    assert settings_from_form("  sk-1 ", " gpt ", " https://x/v1/ ") == (
        ProviderSettings("sk-1", "gpt", "https://x/v1")
    )
    assert settings_from_form("   ", "m", "u").api_key is None


def test_form_to_config_keeps_every_provider_block():
    providers = default_providers()
    providers["openai"] = ProviderSettings(
        "sk-typed", "gpt", "https://api.openai.com/v1"
    )

    cfg = form_to_config("gemini", providers, "English", "en_US", "#000000", "")

    assert cfg.provider == "gemini"
    assert cfg.providers["openai"].api_key == "sk-typed"
    assert cfg.default_deck == "English"


def test_validate_reports_a_missing_key_for_a_provider_that_needs_one():
    assert validate(Config()) == ["Gemini needs an API key."]


def test_validate_accepts_a_keyless_local_provider_with_a_model():
    providers = default_providers()
    providers["local"] = ProviderSettings(None, "llama3.1", "http://localhost:11434/v1")
    cfg = form_to_config("local", providers, "", "en_US", "#2563eb", "")
    assert validate(cfg) == []


def test_validate_reports_an_empty_model_and_a_bad_url():
    providers = default_providers()
    providers["openai"] = ProviderSettings("sk", "", "api.openai.com")
    cfg = form_to_config("openai", providers, "", "en_US", "#2563eb", "")
    assert validate(cfg) == [
        "Choose a model for OpenAI & compatible.",
        "The base URL must start with http:// or https://.",
    ]
