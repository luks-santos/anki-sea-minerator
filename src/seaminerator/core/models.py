from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Sentence:
    text: str
    highlight: str
    note: str = ""


@dataclass(frozen=True)
class WordBlock:
    expression: str
    explanation: str
    translations: list[str]
    grammar_class: str
    sentences: list[Sentence] = field(default_factory=list)


@dataclass(frozen=True)
class ImportedCard:
    front: str
    back: str


def _sentence_from_dict(data: dict) -> Sentence:
    return Sentence(
        text=data["text"],
        highlight=data.get("highlight", ""),
        note=data.get("note", ""),
    )


def _word_from_dict(data: dict) -> WordBlock:
    return WordBlock(
        expression=data["expression"],
        explanation=data.get("explanation", ""),
        translations=list(data.get("translations", [])),
        grammar_class=data.get("grammar_class", ""),
        sentences=[_sentence_from_dict(s) for s in data.get("sentences", [])],
    )


def parse_mining_response(data: dict) -> list[WordBlock]:
    if not isinstance(data, dict) or "words" not in data:
        raise ValueError("mining response must be an object with a 'words' key")
    try:
        return [_word_from_dict(w) for w in data["words"]]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"malformed mining response: {exc}") from exc


def parse_imported_text(text: str) -> tuple[list[ImportedCard], list[str]]:
    stripped = text.strip()
    if not stripped:
        return [], []

    blocks = re.split(r"\n\s*\n", stripped)
    cards: list[ImportedCard] = []
    warnings: list[str] = []
    for i, block in enumerate(blocks, start=1):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) != 2:
            warnings.append(
                f"block {i} skipped: expected 2 lines (front, back), got {len(lines)}"
            )
            continue
        cards.append(ImportedCard(front=lines[0], back=lines[1]))
    return cards, warnings
