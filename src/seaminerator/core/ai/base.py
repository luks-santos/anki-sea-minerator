from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

TRUNCATED_MESSAGE = (
    "the response was cut off by the model's output limit; mine fewer words at a time"
)
OUTSIDE_FORMAT_MESSAGE = (
    "the model returned a response outside the expected format; "
    "use a model that supports structured output"
)

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


class AIError(Exception):
    pass


@dataclass(frozen=True)
class MiningRequest:
    text: str
    schema: dict


class AIProvider(Protocol):
    def mine(self, request: MiningRequest) -> dict: ...

    def list_models(self) -> list[str]: ...


def parse_json_object(text: str) -> dict:
    # Models without real structured output (small local ones especially)
    # sometimes wrap the JSON in a Markdown fence; unwrap it before parsing.
    match = _FENCE.match(text)
    if match:
        text = match.group(1)
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise AIError(OUTSIDE_FORMAT_MESSAGE) from exc
    if not isinstance(data, dict):
        raise AIError(OUTSIDE_FORMAT_MESSAGE)
    return data
