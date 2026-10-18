from __future__ import annotations

from dataclasses import dataclass, replace

from .flow import CardResult
from .models import Sentence, WordBlock, line_spans
from .tags import normalize_tag


@dataclass(frozen=True)
class Summary:
    created: int
    failed: int
    warnings: list[str]
    elapsed: str


def parse_word_list(raw: str) -> list[str]:
    # Repeats are dropped case-insensitively, keeping the first spelling:
    # mining the same word twice pays for it twice and then fails the second
    # card as a duplicate.
    words: dict[str, str] = {}
    for line in raw.splitlines():
        word = line.strip()
        if word and word.lower() not in words:
            words[word.lower()] = word
    return list(words.values())


def start_error(words: list[str], deck: str, native_language: str) -> str | None:
    if not words:
        return "Paste at least one word to mine."
    if not deck:
        return "Choose a target deck."
    if not native_language:
        return "Choose your native language."
    return None


def toggle_selection(
    selection: dict[int, set[int]], w_index: int, s_index: int, checked: bool
) -> None:
    chosen = selection.setdefault(w_index, set())
    if checked:
        chosen.add(s_index)
    else:
        chosen.discard(s_index)


def sentence_details(sentence: Sentence) -> str:
    details = [sentence.note] if sentence.note else []
    if sentence.topics:
        details.append(", ".join(sentence.topics))
    return " · ".join(details)


def import_status(
    card_count: int, warnings: list[str], limit: int = 5, *, highlighted: int = 0
) -> str:
    # Capped so a badly formatted paste can't grow the dialog off-screen.
    status = f"{card_count} card(s) ready"
    if highlighted:
        status += f" · {highlighted} with a highlight"
    if not warnings:
        return status
    lines = warnings[:limit]
    if len(warnings) > limit:
        lines.append(f"…and {len(warnings) - limit} more")
    return f"{status} · {len(warnings)} problem(s):\n" + "\n".join(lines)


Span = tuple[int, int]


def _merged(spans: list[Span]) -> list[Span]:
    merged: list[Span] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        elif start < end:
            merged.append((start, end))
    return merged


def selection_on_lines(text: str, start: int, end: int) -> list[Span]:
    """The parts of a selection in pasted text that fall on card lines."""
    parts = ((max(start, a), min(end, b)) for a, b in line_spans(text))
    return [(a, b) for a, b in parts if a < b]


def toggle_highlights(current: list[Span], selection: list[Span]) -> list[Span]:
    """Ctrl+B in the importer: highlight the selection, or clear it.

    A selection that is already highlighted all the way through is cleared;
    anything else becomes highlighted, joined with the parts it touches.
    """
    current = _merged(current)
    selection = _merged(selection)

    def covered(start: int, end: int) -> bool:
        return any(a <= start and end <= b for a, b in current)

    if selection and all(covered(a, b) for a, b in selection):
        kept: list[Span] = []
        for a, b in current:
            pieces = [(a, b)]
            for s, e in selection:
                pieces = [
                    piece
                    for x, y in pieces
                    for piece in ((x, min(y, s)), (max(x, e), y))
                    if piece[0] < piece[1]
                ]
            kept.extend(pieces)
        return _merged(kept)
    return _merged(current + selection)


def failure_lines(results: list[CardResult]) -> list[str]:
    return [f"{r.expression} — {r.warning}" for r in results if not r.created]


def warning_lines(results: list[CardResult]) -> list[str]:
    # Created cards with something to report (e.g. audio that fell back);
    # failed cards are listed by failure_lines.
    return [f"{r.expression} — {r.warning}" for r in results if r.created and r.warning]


def default_selection(blocks: list[WordBlock]) -> dict[int, set[int]]:
    return {i: {0} for i, b in enumerate(blocks) if b.sentences}


def count_selected(selection: dict[int, set[int]]) -> int:
    return sum(len(indices) for indices in selection.values())


def selected_sentences(
    blocks: list[WordBlock], selection: dict[int, set[int]]
) -> list[tuple[WordBlock, list[Sentence]]]:
    pairs: list[tuple[WordBlock, list[Sentence]]] = []
    for i, block in enumerate(blocks):
        indices = sorted(selection.get(i, set()))
        if not indices:
            continue
        pairs.append((block, [block.sentences[j] for j in indices]))
    return pairs


def apply_class_overrides(
    blocks: list[WordBlock], overrides: dict[int, str]
) -> list[WordBlock]:
    result: list[WordBlock] = []
    for i, block in enumerate(blocks):
        tag = normalize_tag(overrides.get(i, ""))
        if tag and tag != block.class_tag:
            block = replace(block, class_tag=tag)
        result.append(block)
    return result


def format_elapsed(seconds: float) -> str:
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def summarize(results: list[CardResult], elapsed_seconds: float) -> Summary:
    created = sum(1 for r in results if r.created)
    failed = sum(1 for r in results if not r.created)
    warnings = [r.warning for r in results if r.warning]
    return Summary(
        created=created,
        failed=failed,
        warnings=warnings,
        elapsed=format_elapsed(elapsed_seconds),
    )
