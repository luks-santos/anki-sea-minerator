from __future__ import annotations

import httpx

from ..config import PROVIDERS, Config, ConfigError
from .anthropic import AnthropicProvider
from .base import AIProvider
from .gemini import GeminiProvider
from .openai_compat import OpenAICompatProvider


def build_provider(
    config: Config,
    transport: httpx.BaseTransport | None = None,
    *,
    require_model: bool = True,
) -> AIProvider:
    info = PROVIDERS[config.provider]
    settings = config.providers[config.provider]
    if info.needs_key and not settings.api_key:
        raise ConfigError(f"{info.display_name} needs an API key")
    if require_model and not settings.model:
        raise ConfigError(f"choose a model for {info.display_name}")

    key = settings.api_key or ""
    if config.provider == "gemini":
        return GeminiProvider(
            key, settings.model, settings.base_url, transport, info.timeout
        )
    if config.provider == "anthropic":
        return AnthropicProvider(
            key, settings.model, settings.base_url, transport, info.timeout
        )
    return OpenAICompatProvider(
        info.display_name,
        settings.api_key,
        settings.model,
        settings.base_url,
        transport,
        info.timeout,
        unsupported_hint=_LOCAL_HINT if config.provider == "local" else None,
    )


_LOCAL_HINT = (
    "the local server may not support json_schema structured outputs; "
    "update Ollama or LM Studio, or pick a model that supports them"
)
