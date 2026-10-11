from __future__ import annotations

from .core.audio.options import AUDIO_SOURCES, GOOGLE_ACCENTS
from .core.config import (
    PROVIDERS,
    TTS_SPEED_MAX,
    TTS_SPEED_MIN,
    AudioSettings,
    Config,
    ConfigError,
    ProviderSettings,
    voice_names,
)
from .core.languages import NATIVE_LANGUAGES

_TOP_LEVEL_STRINGS = ("default_deck", "tts_lang", "highlight_color")


def config_from_dict(data: dict) -> Config:
    # Strict on purpose: there is exactly one config shape. Unknown top-level
    # keys are ignored because Anki merges shipped defaults into a stored
    # config at the top level only, so stale keys can linger.
    provider = data.get("provider")
    if provider not in PROVIDERS:
        raise ConfigError(f"unknown provider {provider!r}")

    blocks = data.get("providers")
    if not isinstance(blocks, dict):
        raise ConfigError("the config has no 'providers' block")

    providers: dict[str, ProviderSettings] = {}
    for provider_id, info in PROVIDERS.items():
        block = blocks.get(provider_id)
        if block is None:
            # A stored `providers` block replaces the shipped one wholesale
            # (Anki merges only top-level keys), so a provider added in a
            # later version is missing here; use its defaults.
            providers[provider_id] = info.default
            continue
        if not isinstance(block, dict):
            raise ConfigError(f"the config has no settings for {provider_id!r}")
        model, base_url = block.get("model"), block.get("base_url")
        if not isinstance(model, str) or not isinstance(base_url, str):
            raise ConfigError(f"invalid model or base_url for {provider_id!r}")
        key = block.get("api_key")
        api_key = key.strip() if isinstance(key, str) and key.strip() else None
        providers[provider_id] = ProviderSettings(api_key, model, base_url)

    values: dict[str, str] = {}
    defaults = Config()
    for name in _TOP_LEVEL_STRINGS:
        value = data.get(name, getattr(defaults, name))
        if not isinstance(value, str):
            raise ConfigError(f"{name!r} must be text")
        values[name] = value

    voices, speed = _voice(data)
    return Config(
        provider=provider,
        providers=providers,
        tts_voices=voices,
        tts_speed=speed,
        native_language=_native_language(data),
        prompts=_prompts(data),
        audio=_audio(data),
        **values,
    )


def _voice(data: dict) -> tuple[tuple[str, ...], float]:
    voices = data.get("tts_voices", [])
    if not isinstance(voices, list) or not all(isinstance(v, str) for v in voices):
        raise ConfigError("'tts_voices' must be a list of voice names")

    speed = data.get("tts_speed", Config().tts_speed)
    # bool is an int in Python; `true` in the JSON is not a speed.
    if (
        isinstance(speed, bool)
        or not isinstance(speed, (int, float))
        or not TTS_SPEED_MIN <= speed <= TTS_SPEED_MAX
    ):
        raise ConfigError(
            f"'tts_speed' must be a number from {TTS_SPEED_MIN} to {TTS_SPEED_MAX}"
        )
    return voice_names(voices), float(speed)


def _native_language(data: dict) -> str:
    code = data.get("native_language", "")
    if not isinstance(code, str) or (code and code not in NATIVE_LANGUAGES):
        raise ConfigError(f"unknown native language {code!r}")
    return code


def _prompts(data: dict) -> dict[str, str]:
    prompts = data.get("prompts", {})
    if not isinstance(prompts, dict):
        raise ConfigError("'prompts' must be an object of prompt texts")
    result: dict[str, str] = {}
    for code, text in prompts.items():
        if code not in NATIVE_LANGUAGES:
            raise ConfigError(f"'prompts' has an unknown language {code!r}")
        if not isinstance(text, str):
            raise ConfigError(f"the prompt for {code!r} must be text")
        # A blank edit means "no edit": the default prompt applies.
        if text.strip():
            result[code] = text
    return result


def with_native_language(data: dict, code: str) -> dict:
    """The stored config with only the native language changed.

    Works on the raw dict, so saving the choice from the mining screen keeps
    every other key as stored, even in a config that doesn't parse.
    """
    updated = dict(data)
    updated["native_language"] = code
    return updated


def _audio(data: dict) -> AudioSettings:
    block = data.get("audio", {})
    if not isinstance(block, dict):
        raise ConfigError("'audio' must be an object")
    defaults = AudioSettings()
    source = block.get("source", defaults.source)
    if not isinstance(source, str) or source not in AUDIO_SOURCES:
        raise ConfigError(f"unknown audio source {source!r}")
    google = _audio_block(block, "google")
    gemini = _audio_block(block, "gemini")
    accent = google.get("accent", defaults.google_accent)
    if not isinstance(accent, str) or accent not in GOOGLE_ACCENTS:
        raise ConfigError(f"unknown Google Translate accent {accent!r}")
    return AudioSettings(
        source=source,
        google_accent=accent,
        gemini_voice=_gemini_text(gemini, "voice", defaults.gemini_voice),
        gemini_model=_gemini_text(gemini, "model", defaults.gemini_model),
    )


def _audio_block(block: dict, name: str) -> dict:
    # A stored "audio" replaces the shipped one wholesale (Anki merges only
    # top-level keys), so a missing sub-block or key takes its default.
    sub = block.get(name, {})
    if not isinstance(sub, dict):
        raise ConfigError(f"'audio.{name}' must be an object")
    return sub


def _gemini_text(block: dict, key: str, default: str) -> str:
    value = block.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"the Gemini {key} must be text")
    return value.strip()


def _audio_dict(audio: AudioSettings) -> dict:
    return {
        "source": audio.source,
        "google": {"accent": audio.google_accent},
        "gemini": {"voice": audio.gemini_voice, "model": audio.gemini_model},
    }


def _readable_audio(data: dict) -> AudioSettings:
    try:
        return _audio(data)
    except ConfigError:
        return AudioSettings()


def display_config(data: dict) -> Config:
    """The config for screens that don't need a working AI provider.

    A broken provider block must not reset tts_lang, the voice,
    default_deck, the native language, the edited prompts or the audio
    settings to defaults: importing would then rewrite the note type's audio.
    """
    # Unreadable language and audio settings are dropped before parsing, so
    # they never cost the provider blocks: Save would otherwise wipe every
    # API key.
    repaired = dict(data)
    repaired["native_language"] = _readable_language(data)
    repaired["prompts"] = _readable_prompts(data)
    repaired["audio"] = _audio_dict(_readable_audio(data))
    try:
        return config_from_dict(repaired)
    except ConfigError:
        values = {
            name: data[name]
            for name in _TOP_LEVEL_STRINGS
            if isinstance(data.get(name), str)
        }
        try:
            voices, speed = _voice(data)
        except ConfigError:
            voices, speed = Config().tts_voices, Config().tts_speed
        return Config(
            tts_voices=voices,
            tts_speed=speed,
            native_language=repaired["native_language"],
            prompts=repaired["prompts"],
            audio=_readable_audio(data),
            **values,
        )


def _readable_language(data: dict) -> str:
    try:
        return _native_language(data)
    except ConfigError:
        return ""


def _readable_prompts(data: dict) -> dict[str, str]:
    # Entry by entry: one bad entry must not cost the user's other edits.
    prompts = data.get("prompts", {})
    if not isinstance(prompts, dict):
        return {}
    return {
        code: text
        for code, text in prompts.items()
        if code in NATIVE_LANGUAGES and isinstance(text, str) and text.strip()
    }


def config_to_dict(config: Config) -> dict:
    return {
        "provider": config.provider,
        "providers": {
            provider_id: {
                "api_key": settings.api_key or "",
                "model": settings.model,
                "base_url": settings.base_url,
            }
            for provider_id, settings in config.providers.items()
        },
        "default_deck": config.default_deck,
        "tts_lang": config.tts_lang,
        "tts_voices": list(config.tts_voices),
        "tts_speed": config.tts_speed,
        "highlight_color": config.highlight_color,
        "native_language": config.native_language,
        "prompts": dict(config.prompts),
        "audio": _audio_dict(config.audio),
    }
