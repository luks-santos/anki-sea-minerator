from __future__ import annotations

from .config import PROVIDERS, Config, ProviderSettings


def visible_fields(provider_id: str) -> set[str]:
    fields = {"api_key", "model"}
    if PROVIDERS[provider_id].base_url_editable:
        fields.add("base_url")
    return fields


def settings_from_form(api_key: str, model: str, base_url: str) -> ProviderSettings:
    key = api_key.strip()
    return ProviderSettings(
        api_key=key or None,
        model=model.strip(),
        base_url=base_url.strip().rstrip("/"),
    )


def form_to_config(
    provider: str,
    providers: dict[str, ProviderSettings],
    default_deck: str,
    tts_lang: str,
    highlight_color: str,
    prompt_path: str,
) -> Config:
    return Config(
        provider=provider,
        providers=dict(providers),
        default_deck=default_deck,
        tts_lang=tts_lang.strip(),
        highlight_color=highlight_color.strip(),
        prompt_path=prompt_path,
    )


def validate(config: Config) -> list[str]:
    info = PROVIDERS[config.provider]
    settings = config.providers[config.provider]
    problems = []
    if info.needs_key and not settings.api_key:
        problems.append(f"{info.display_name} needs an API key.")
    if not settings.model:
        problems.append(f"Choose a model for {info.display_name}.")
    if not settings.base_url.startswith(("http://", "https://")):
        problems.append("The base URL must start with http:// or https://.")
    return problems
