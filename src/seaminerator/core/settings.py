from __future__ import annotations

import copy

from .config import PROVIDERS, Config, ProviderSettings

# Shown in the Advanced… JSON instead of a stored key; left untouched, it
# means "keep the key", so the raw editor never displays secrets.
KEY_MASK = "•••••• (unchanged)"

# Substrings of model ids that can't mine (embeddings, speech, images,
# moderation); dropped from the model dropdown.
_NON_CHAT_MODEL_HINTS = (
    "embed",
    "tts",
    "whisper",
    "dall-e",
    "moderation",
    "transcribe",
    "image",
)


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


def mask_keys(data: dict) -> dict:
    masked = copy.deepcopy(data)
    for block in masked.get("providers", {}).values():
        if isinstance(block, dict) and block.get("api_key"):
            block["api_key"] = KEY_MASK
    return masked


def unmask_keys(edited: dict, original: dict) -> dict:
    restored = copy.deepcopy(edited)
    blocks = restored.get("providers")
    originals = original.get("providers")
    if not isinstance(blocks, dict) or not isinstance(originals, dict):
        return restored  # config_from_dict reports the malformed value
    for provider_id, block in blocks.items():
        if isinstance(block, dict) and block.get("api_key") == KEY_MASK:
            block["api_key"] = originals.get(provider_id, {}).get("api_key", "")
    return restored


def model_choices(models: list[str]) -> list[str]:
    unique = sorted(set(models))
    chat = [
        model
        for model in unique
        if not any(hint in model.lower() for hint in _NON_CHAT_MODEL_HINTS)
    ]
    # A service whose ids all look non-chat is unusual; show everything
    # rather than an empty list.
    return chat or unique
