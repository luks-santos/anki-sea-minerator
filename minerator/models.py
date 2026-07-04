from __future__ import annotations

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
