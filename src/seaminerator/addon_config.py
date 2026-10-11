from __future__ import annotations

from .core.config import (
    PROVIDERS,
    TTS_SPEED_MAX,
    TTS_SPEED_MIN,
    Config,
    ConfigError,
    ProviderSettings,
    voice_names,
)
from .core.languages import NATIVE_LANGUAGES

_TOP_LEVEL_STRINGS = ("default_deck", "tts_lang", "highlight_color", "prompt_path")


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


def display_config(data: dict) -> Config:
    """The config for screens that don't need a working AI provider.

    A broken provider block must not reset tts_lang, the voice,
    default_deck, the native language or the edited prompts to defaults:
    importing would then rewrite the note type's audio.
    """
    try:
        return config_from_dict(data)
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
        try:
            native_language = _native_language(data)
        except ConfigError:
            native_language = ""
        try:
            prompts = _prompts(data)
        except ConfigError:
            prompts = {}
        return Config(
            tts_voices=voices,
            tts_speed=speed,
            native_language=native_language,
            prompts=prompts,
            **values,
        )


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
        "prompt_path": config.prompt_path,
    }
