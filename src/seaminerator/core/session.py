from __future__ import annotations

from dataclasses import dataclass

from .flow import CardResult
from .models import Sentence, WordBlock


@dataclass(frozen=True)
class Summary:
    created: int
    failed: int
    warnings: list[str]
    elapsed: str


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
