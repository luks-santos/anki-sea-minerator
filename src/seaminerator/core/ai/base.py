from __future__ import annotations

from typing import Protocol

from ..models import WordBlock


class AIConnector(Protocol):
    def mine(self, words: list[str], prompt: str) -> list[WordBlock]: ...
