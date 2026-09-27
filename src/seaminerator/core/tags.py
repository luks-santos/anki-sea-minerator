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


# Topics offered to Gemini even when the collection has no tags, so the model
# reuses one name per structure instead of coining a new variant every run.
BASE_TOPICS: tuple[str, ...] = (
    "present-simple",
    "present-continuous",
    "present-perfect",
    "past-simple",
    "past-continuous",
    "future-simple",
    "verb-to-be",
    "have-got",
    "modal-verbs",
    "conditionals",
    "passive-voice",
    "imperative",
    "infinitive",
    "gerund",
)


def topic_vocabulary(all_tags: list[str]) -> list[str]:
    excluded = set(CLASS_TAGS) | RESERVED_TAGS
    # Keyed by lowercase so a collection tag like `Past-Simple` replaces the
    # base `past-simple` instead of sitting next to it.
    topics = {topic: topic for topic in BASE_TOPICS}
    for tag in all_tags:
        if tag.lower() not in excluded:
            topics[tag.lower()] = tag
    return sorted(topics.values(), key=str.lower)


def class_label(tag: str) -> str:
    return tag.replace("-", " ").capitalize()
