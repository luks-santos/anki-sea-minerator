from __future__ import annotations

import hashlib
import re

from minerator.models import WordBlock

_BRACKET_TAG_RE = re.compile(r"^\[[^\]]*\]\s*")


def strip_bracket_tag(text: str) -> str:
    return _BRACKET_TAG_RE.sub("", text, count=1)


def highlight_html(text: str, highlight: str, color: str) -> str:
    if not highlight:
        return text
    match = re.search(re.escape(highlight), text, re.IGNORECASE)
    if not match:
        return text
    start, end = match.span()
    span = f'<span style="color:{color}">{text[start:end]}</span>'
    return text[:start] + span + text[end:]


def audio_filename(text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
    return f"minerator-{digest}.mp3"


def build_front(highlighted_text: str, audio_file: str | None) -> str:
    if audio_file:
        return f"{highlighted_text} [sound:{audio_file}]"
    return highlighted_text


def build_back(word: WordBlock) -> str:
    translations = ", ".join(word.translations)
    expression = word.expression
    capitalized = expression[:1].upper() + expression[1:] if expression else expression
    return f"{capitalized}: {translations} ({word.grammar_class})"
