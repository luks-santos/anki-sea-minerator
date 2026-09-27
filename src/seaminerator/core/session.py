from __future__ import annotations

from dataclasses import dataclass, replace

from .flow import CardResult
from .models import Sentence, WordBlock
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


def start_error(words: list[str], deck: str) -> str | None:
    if not words:
        return "Paste at least one word to mine."
    if not deck:
        return "Choose a target deck."
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
