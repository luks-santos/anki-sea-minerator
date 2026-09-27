import dataclasses
import json
from pathlib import Path

import pytest

from seaminerator.addon_config import config_from_dict
from seaminerator.core.ai.anthropic import AnthropicProvider
from seaminerator.core.ai.gemini import GeminiProvider
from seaminerator.core.ai.openai_compat import OpenAICompatProvider
from seaminerator.core.ai.registry import build_provider
from seaminerator.core.config import Config, ConfigError, ProviderSettings

SHIPPED = Path(__file__).parent.parent.parent / "src" / "seaminerator" / "config.json"


def config(provider, api_key="k", model="m"):
    base = Config()
    settings = dataclasses.replace(
        base.providers[provider], api_key=api_key, model=model
    )
    providers = {**base.providers, provider: settings}
    return dataclasses.replace(base, provider=provider, providers=providers)


@pytest.mark.parametrize(
    ("provider", "cls"),
    [
        ("gemini", GeminiProvider),
        ("openai", OpenAICompatProvider),
        ("anthropic", AnthropicProvider),
        ("local", OpenAICompatProvider),
    ],
)
def test_builds_the_adapter_for_each_provider(provider, cls):
    assert isinstance(build_provider(config(provider)), cls)


def test_missing_required_key_is_a_config_error():
    with pytest.raises(ConfigError, match="API key"):
        build_provider(config("anthropic", api_key=None))


def test_local_builds_without_a_key():
    assert isinstance(
        build_provider(config("local", api_key=None)), OpenAICompatProvider
    )


def test_empty_model_is_a_config_error():
    with pytest.raises(ConfigError, match="model"):
        build_provider(config("openai", model=""))


def test_listing_models_does_not_need_a_model():
    provider = build_provider(config("openai", model=""), require_model=False)
    assert isinstance(provider, OpenAICompatProvider)


def test_legacy_merged_config_reads_and_then_needs_a_key():
    # Anki merges shipped defaults into a stored config at the top level,
    # so today's config arrives as the new defaults plus the old flat keys.
    data = json.loads(SHIPPED.read_text(encoding="utf-8"))
    data.update({"gemini_api_key": "old", "model": "gemini-2.5-flash"})

    cfg = config_from_dict(data)

    assert cfg.providers["gemini"] == ProviderSettings(
        None, "gemini-2.5-flash", "https://generativelanguage.googleapis.com/v1beta"
    )
    with pytest.raises(ConfigError, match="API key"):
        build_provider(cfg)
