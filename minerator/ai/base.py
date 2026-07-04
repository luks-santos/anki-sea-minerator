from __future__ import annotations

from typing import Protocol

from minerator.models import WordBlock


class AIConnector(Protocol):
    def mine(self, words: list[str], prompt: str) -> list[WordBlock]: ...
