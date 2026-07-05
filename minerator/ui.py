from __future__ import annotations

from rich.console import Console
from rich.markup import escape
from rich.theme import Theme

from minerator.cards import build_back
from minerator.models import WordBlock

THEME = Theme(
    {
        "mnr.heading": "bold cyan",
        "mnr.grammar": "dim magenta",
        "mnr.label": "dim",
        "mnr.explanation": "bright_white",
        "mnr.translation": "green",
        "mnr.note": "dim italic",
        "mnr.success": "green",
        "mnr.warning": "yellow",
        "mnr.error": "red",
    }
)

console = Console(theme=THEME)


def render_block(block: WordBlock) -> None:
    console.rule(style="mnr.label")
    grammar = f"  [mnr.grammar]{escape(block.grammar_class)}[/]" if block.grammar_class else ""
    console.print(f" [mnr.heading]{escape(block.expression)}[/]{grammar}")
    console.print()
    if block.explanation:
        console.print(f" [mnr.label]Meaning[/]     [mnr.explanation]{escape(block.explanation)}[/]")
    if block.translations:
        pt = " · ".join(escape(t) for t in block.translations)
        console.print(f" [mnr.label]PT[/]          [mnr.translation]{pt}[/]")
    console.print(f" [mnr.label]Card back[/]   [dim]{escape(build_back(block))}[/]")
    console.print()
