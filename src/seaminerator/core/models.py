from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from .tags import CLASS_TAGS, RESERVED_TAGS, normalize_tag


@dataclass(frozen=True)
class Sentence:
    text: str
    highlight: str
    note: str = ""
    topics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WordBlock:
    expression: str
    explanation: str
    translations: list[str]
    class_tag: str
    sentences: list[Sentence] = field(default_factory=list)


@dataclass(frozen=True)
class ImportedCard:
    front: str
    back: str


def _require_str(value: object, field_name: str) -> str:
    # Dataclasses don't enforce their annotations, so a schema-violating
    # model response (e.g. `"text": null`) would otherwise sail straight
    # into a frozen Sentence/WordBlock and blow up much later, unguarded,
    # in core.cards.highlight_html/build_back. Catching it here, at parse
    # time, keeps every downstream consumer able to trust these fields.
    if not isinstance(value, str):
        raise ValueError(
            f"expected a string for '{field_name}', got {type(value).__name__}"
        )
    return value


def _class_tag_from(value: object) -> str:
    tag = normalize_tag(_require_str(value, "class_tag"))
    if not tag:
        raise ValueError("'class_tag' is empty after normalization")
    return tag


def _topics_from(value: object, existing: dict[str, str]) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"expected a list for 'topics', got {type(value).__name__}")
    topics: list[str] = []
    for item in value:
        topic = normalize_tag(_require_str(item, "topics"))
        if not topic or topic in RESERVED_TAGS or topic in CLASS_TAGS:
            continue
        # Anki merges tags that differ only by case, but not `Verb_To_Be` and
        # `verb-to-be`: map back to the collection's own spelling so
        # normalization never mints a near-duplicate of an existing tag.
        topic = existing.get(topic, topic)
        if topic not in topics:
            topics.append(topic)
    return topics


def _sentence_from_dict(data: dict, existing: dict[str, str]) -> Sentence:
    return Sentence(
        text=_require_str(data["text"], "text"),
        highlight=_require_str(data.get("highlight", ""), "highlight"),
        note=_require_str(data.get("note", ""), "note"),
        topics=_topics_from(data.get("topics"), existing),
    )


def _word_from_dict(data: dict, existing: dict[str, str]) -> WordBlock:
    translations = list(data.get("translations", []))
    for translation in translations:
        _require_str(translation, "translations")
    return WordBlock(
        expression=_require_str(data["expression"], "expression"),
        explanation=_require_str(data.get("explanation", ""), "explanation"),
        translations=translations,
        class_tag=_class_tag_from(data.get("class_tag")),
        sentences=[_sentence_from_dict(s, existing) for s in data.get("sentences", [])],
    )


def parse_mining_response(
    data: dict, vocabulary: Sequence[str] = ()
) -> list[WordBlock]:
    if not isinstance(data, dict) or "words" not in data:
        raise ValueError("mining response must be an object with a 'words' key")
    existing = {normalize_tag(tag): tag for tag in vocabulary}
    try:
        return [_word_from_dict(w, existing) for w in data["words"]]
    except (KeyError, TypeError, AttributeError) as exc:
        # AttributeError covers a non-object entry in "words": the first thing
        # _word_from_dict touches is data.get(...), so a bare string or number
        # raises AttributeError rather than TypeError.
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
