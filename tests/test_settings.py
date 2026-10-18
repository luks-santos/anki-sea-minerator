import pytest

from seaminerator.core.audio.options import GEMINI_KEY_MESSAGE
from seaminerator.core.config import (
    AudioSettings,
    Config,
    ProviderSettings,
    default_providers,
)
from seaminerator.core.settings import (
    KEY_MASK,
    audio_note,
    form_to_config,
    mask_keys,
    model_choices,
    prompt_status,
    settings_from_form,
    store_prompt,
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

    cfg = form_to_config("gemini", providers, "English", "en_US", "#000000")

    assert cfg.provider == "gemini"
    assert cfg.providers["openai"].api_key == "sk-typed"
    assert cfg.default_deck == "English"


def test_validate_reports_a_missing_key_for_a_provider_that_needs_one():
    assert validate(Config()) == ["Gemini needs an API key."]


def test_validate_accepts_a_keyless_local_provider_with_a_model():
    providers = default_providers()
    providers["local"] = ProviderSettings(None, "llama3.1", "http://localhost:11434/v1")
    cfg = form_to_config("local", providers, "", "en_US", "#2563eb")
    assert validate(cfg) == []


def test_validate_reports_an_empty_model_and_a_bad_url():
    providers = default_providers()
    providers["openai"] = ProviderSettings("sk", "", "api.openai.com")
    cfg = form_to_config("openai", providers, "", "en_US", "#2563eb")
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


def test_form_to_config_carries_the_language_and_prompts():
    prompts = {"es": "Mi prompt"}

    cfg = form_to_config(
        "gemini",
        default_providers(),
        "",
        "en_US",
        "#2563eb",
        native_language="es",
        prompts=prompts,
    )

    assert cfg.native_language == "es"
    assert cfg.prompts == {"es": "Mi prompt"}
    assert cfg.prompts is not prompts


def test_store_prompt_keeps_an_edit():
    assert store_prompt({}, "es", "Mi prompt", "Default") == {"es": "Mi prompt"}


def test_store_prompt_removes_an_edit_equal_to_the_default():
    # Surrounding whitespace doesn't make an edit: storing the default would
    # pin the user to it when a later version improves it.
    stored = store_prompt(
        {"es": "old", "fr": "x"}, "es", "\n  Default\n\n", "Default\n"
    )
    assert stored == {"fr": "x"}


def test_store_prompt_rejects_blank_text():
    with pytest.raises(ValueError, match="can't be empty"):
        store_prompt({"es": "old"}, "es", " \n ", "Default")


def test_store_prompt_does_not_change_its_input():
    prompts = {"es": "old"}
    store_prompt(prompts, "es", "new", "Default")
    assert prompts == {"es": "old"}


def test_prompt_status_follows_the_text():
    assert prompt_status("Default\n", "Default") == "Default"
    assert prompt_status("Mine", "Default") == "Customized"


def test_form_to_config_carries_the_audio_settings():
    audio = AudioSettings(source="google", google_accent="co.in")

    cfg = form_to_config(
        "gemini", default_providers(), "", "en_US", "#2563eb", audio=audio
    )

    assert cfg.audio == audio


def with_gemini_key(providers):
    base_url = providers["gemini"].base_url
    providers["gemini"] = ProviderSettings("g-key", "gemini-2.5-flash", base_url)
    return providers


def test_validate_requires_a_gemini_key_for_gemini_audio():
    providers = default_providers()
    providers["openai"] = ProviderSettings("sk", "gpt", "https://api.openai.com/v1")
    audio = AudioSettings(source="gemini")

    without_key = Config(provider="openai", providers=providers, audio=audio)
    assert GEMINI_KEY_MESSAGE in validate(without_key)

    with_key = Config(
        provider="openai", providers=with_gemini_key(providers), audio=audio
    )
    assert validate(with_key) == []


def test_validate_requires_a_gemini_voice_and_model():
    audio = AudioSettings(source="gemini", gemini_voice=" ", gemini_model="")

    problems = validate(
        Config(providers=with_gemini_key(default_providers()), audio=audio)
    )

    assert "Choose a Gemini voice." in problems
    assert "Choose a Gemini TTS model." in problems


def test_a_preview_error_shows_above_the_privacy_note_instead_of_hiding_it():
    note = audio_note("google", lame_found=True, error="Google Translate is down")

    assert note.startswith("✗ Google Translate is down")
    assert "sent to Google Translate (an unofficial endpoint)" in note


def test_the_gemini_note_mentions_lame_only_when_it_is_missing():
    assert "LAME was not found" in audio_note("gemini", lame_found=False)
    assert "LAME" not in audio_note("gemini", lame_found=True)


def test_the_system_voice_sends_nothing_so_it_has_no_note():
    assert audio_note("system", lame_found=True) == ""


def test_form_to_config_carries_the_topic_badge_choice():
    cfg = form_to_config(
        "gemini", default_providers(), "", "en_US", "#2563eb", topic_badge=False
    )
    assert cfg.topic_badge is False
