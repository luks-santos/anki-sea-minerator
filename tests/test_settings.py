from seaminerator.core.config import Config, ProviderSettings, default_providers
from seaminerator.core.settings import (
    KEY_MASK,
    form_to_config,
    mask_keys,
    model_choices,
    settings_from_form,
    unmask_keys,
    validate,
    visible_fields,
    voice_choices,
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


def advanced_data():
    return {
        "provider": "gemini",
        "providers": {
            "gemini": {"api_key": "AIza-secret", "model": "m", "base_url": "u"},
            "local": {"api_key": "", "model": "", "base_url": "u"},
        },
    }


def test_mask_keys_hides_set_keys_and_leaves_blank_ones():
    masked = mask_keys(advanced_data())
    assert masked["providers"]["gemini"]["api_key"] == KEY_MASK
    assert masked["providers"]["local"]["api_key"] == ""
    assert advanced_data()["providers"]["gemini"]["api_key"] == "AIza-secret"


def test_unmask_keys_restores_untouched_masks_and_keeps_edits():
    original = advanced_data()
    edited = mask_keys(original)
    edited["providers"]["local"]["api_key"] = "typed-in-json"

    restored = unmask_keys(edited, original)

    assert restored["providers"]["gemini"]["api_key"] == "AIza-secret"
    assert restored["providers"]["local"]["api_key"] == "typed-in-json"


def test_model_choices_sorts_dedups_and_drops_non_chat_models():
    models = [
        "gpt-b",
        "text-embedding-3-small",
        "gpt-a",
        "tts-1",
        "whisper-1",
        "dall-e-3",
        "omni-moderation-latest",
        "gpt-a",
    ]
    assert model_choices(models) == ["gpt-a", "gpt-b"]


def test_model_choices_keeps_everything_when_the_filter_would_empty_it():
    assert model_choices(["tts-b", "tts-a"]) == ["tts-a", "tts-b"]


def test_unmask_keys_passes_a_malformed_providers_value_through():
    # config_from_dict then reports it; unmasking must not crash first.
    edited = {"provider": "gemini", "providers": "oops"}
    assert unmask_keys(edited, advanced_data()) == edited


def test_form_to_config_reads_comma_separated_voices_and_the_speed():
    cfg = form_to_config(
        "gemini",
        default_providers(),
        "",
        "en_US",
        "#2563eb",
        "",
        tts_voices=" Microsoft_Zira, ,Apple_Samantha,",
        tts_speed=0.9,
    )
    assert cfg.tts_voices == ("Microsoft_Zira", "Apple_Samantha")
    assert cfg.tts_speed == 0.9


def test_voice_choices_lists_each_voice_of_the_language_once_sorted():
    # SAPI and WinRT both report David and Zira on Windows.
    installed = [
        ("Microsoft_Zira", "en_US"),
        ("Microsoft_David", "en_US"),
        ("Microsoft_Hazel", "en_GB"),
        ("Microsoft_David", "en_US"),
    ]
    assert voice_choices(installed, "en_US") == ["Microsoft_David", "Microsoft_Zira"]


def test_voice_choices_is_empty_without_voices_for_the_language():
    assert voice_choices([("Microsoft_Zira", "en_US")], "pt_BR") == []
