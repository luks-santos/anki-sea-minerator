from __future__ import annotations

import hashlib

from minerator.models import WordBlock


def highlight_html(text: str, highlight: str, color: str) -> str:
    if not highlight:
        return text
    idx = text.lower().find(highlight.lower())
    if idx == -1:
        return text
    match = text[idx : idx + len(highlight)]
    span = f'<span style="color:{color}">{match}</span>'
    return text[:idx] + span + text[idx + len(highlight) :]


def audio_filename(text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
    return f"minerator-{digest}.mp3"


def build_front(
    sentence_text: str, highlight: str, color: str, audio_file: str | None
) -> str:
    html = highlight_html(sentence_text, highlight, color)
    if audio_file:
        html = f"{html} [sound:{audio_file}]"
    return html


def build_back(word: WordBlock) -> str:
    translations = ", ".join(word.translations)
    return f"{word.expression.capitalize()}: {translations} ({word.grammar_class})"
