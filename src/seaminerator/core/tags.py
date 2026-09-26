from __future__ import annotations

import re
import unicodedata

ORIGIN_TAG = "anki-sea-minerator"

CLASS_TAGS: tuple[str, ...] = (
    "noun",
    "verb",
    "adjective",
    "adverb",
    "pronoun",
    "determiner",
    "preposition",
    "conjunction",
    "interjection",
    "phrasal-verb",
    "idiom",
    "expression",
)

# Tags that are never grammar topics: the add-on's own origin tag and the two
# Anki itself manages (leech detection and the "mark note" action).
RESERVED_TAGS: frozenset[str] = frozenset({ORIGIN_TAG, "leech", "marked"})


def normalize_tag(raw: str) -> str:
    # NFKD splits "í" into "i" + a combining accent, which the ASCII encode
    # then drops. `:` survives so a hierarchical tag like `grammar::tense`
    # is not flattened into `grammartense`.
    ascii_text = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode()
    tag = ascii_text.strip().lower()
    tag = re.sub(r"[\s_/]+", "-", tag)
    tag = re.sub(r"[^a-z0-9:-]", "", tag)
    tag = re.sub(r"-{2,}", "-", tag)
    return tag.strip("-:")


def topic_vocabulary(all_tags: list[str]) -> list[str]:
    excluded = set(CLASS_TAGS) | RESERVED_TAGS
    return sorted(
        (tag for tag in all_tags if tag.lower() not in excluded), key=str.lower
    )


def class_label(tag: str) -> str:
    return tag.replace("-", " ").capitalize()


def card_tags(class_tag: str, topics: list[str]) -> list[str]:
    tags = [ORIGIN_TAG, class_tag]
    for topic in topics:
        if topic and topic not in RESERVED_TAGS and topic not in tags:
            tags.append(topic)
    return tags
