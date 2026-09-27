from __future__ import annotations

import re

from .models import WordBlock
from .tags import class_label


def highlight_html(text: str, highlight: str, color: str) -> str:
    if not highlight:
        return text
    match = re.search(re.escape(highlight), text, re.IGNORECASE)
    if not match:
        return text
    start, end = match.span()
    span = f'<span style="color:{color}">{text[start:end]}</span>'
    return text[:start] + span + text[end:]


def build_back(word: WordBlock, topics: list[str] | None = None) -> str:
    translations = ", ".join(word.translations)
    expression = word.expression
    capitalized = expression[:1].upper() + expression[1:] if expression else expression
    grammar = class_label(word.class_tag)
    if topics:
        grammar += " · " + ", ".join(topics)
    return f"{capitalized}: {translations} ({grammar})"
