from __future__ import annotations

from .core.config import PROVIDERS, Config, ConfigError, ProviderSettings

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

    return Config(provider=provider, providers=providers, **values)


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
        "highlight_color": config.highlight_color,
        "prompt_path": config.prompt_path,
    }
