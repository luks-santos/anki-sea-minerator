from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..models import WordBlock


class AIConnector(Protocol):
    def mine(
        self, words: list[str], prompt: str, topics: Sequence[str] = ()
    ) -> list[WordBlock]: ...
