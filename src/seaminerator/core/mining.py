from __future__ import annotations

from collections.abc import Sequence

from .ai.base import OUTSIDE_FORMAT_MESSAGE, AIError, AIProvider, MiningRequest
from .ai.schema import mining_schema
from .models import WordBlock, parse_mining_response
from .prompt import tagging_instructions


def build_request(
    words: list[str], prompt: str, topics: Sequence[str]
) -> MiningRequest:
    text = (
        f"{prompt}\n\n{tagging_instructions(list(topics))}\n\nList of the day:\n"
        + "\n".join(words)
    )
    return MiningRequest(text=text, schema=mining_schema())


def mine_words(
    provider: AIProvider, words: list[str], prompt: str, topics: Sequence[str]
) -> list[WordBlock]:
    data = provider.mine(build_request(words, prompt, topics))
    try:
        return parse_mining_response(data, topics)
    except (ValueError, TypeError) as exc:
        raise AIError(f"{OUTSIDE_FORMAT_MESSAGE} ({exc})") from exc
