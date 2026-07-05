from __future__ import annotations

from contextlib import contextmanager

from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from questionary.prompts.common import Choice, InquirerControl, create_inquirer_layout
from questionary.styles import merge_styles_default
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.theme import Theme

from minerator.cards import build_back
from minerator.models import Sentence, WordBlock

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

console = Console(theme=THEME, highlight=False)


def render_block(block: WordBlock) -> None:
    console.rule(style="mnr.label")
    grammar = (
        f"  [mnr.grammar]{escape(block.grammar_class)}[/]"
        if block.grammar_class
        else ""
    )
    console.print(f" [mnr.heading]{escape(block.expression)}[/]{grammar}")
    console.print()

    table = Table.grid(padding=(0, 2, 0, 1), pad_edge=True)
    table.add_column(style="mnr.label", no_wrap=True)
    table.add_column()
    if block.explanation:
        table.add_row("Meaning", f"[mnr.explanation]{escape(block.explanation)}[/]")
    if block.translations:
        pt = " · ".join(escape(t) for t in block.translations)
        table.add_row("PT", f"[mnr.translation]{pt}[/]")
    if block.explanation or block.translations:
        table.add_row("", "")
    table.add_row("Card back", f"[dim]{escape(build_back(block))}[/]")
    console.print(table)
    console.print()


def _lines_to_words(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def read_words() -> list[str]:
    bindings = KeyBindings()

    @bindings.add(Keys.Enter, eager=True)
    def _submit(event):
        event.current_buffer.validate_and_handle()

    @bindings.add("escape", "enter")  # Alt+Enter
    @bindings.add(Keys.ControlJ)  # Ctrl+J
    def _newline(event):
        event.current_buffer.insert_text("\n")

    console.print()
    console.print(
        " [mnr.heading]Words of the day[/]"
        "  [mnr.label]· Enter to mine · Alt+Enter or Ctrl+J for a new line[/]"
    )
    session: PromptSession = PromptSession(multiline=True, key_bindings=bindings)
    try:
        text = session.prompt(" › ")
    except (KeyboardInterrupt, EOFError):
        return []
    return _lines_to_words(text)


@contextmanager
def mining_status(word_count: int):
    with console.status(
        "[mnr.label]Connecting to Gemini…[/]", spinner="dots"
    ) as status:
        status.update(f"[mnr.label]Mining {word_count} words…[/]")
        yield
    console.print(f" [mnr.success]✓ {word_count} words mined[/]")


@contextmanager
def creating_cards_status(card_count: int):
    with console.status(
        f"[mnr.label]Creating {card_count} card(s)…[/]", spinner="dots"
    ):
        yield


_SKIP = object()


def _resolve_selection(checked: list, pointed) -> list[Sentence]:
    if any(value is _SKIP for value in checked):
        return []
    real = [value for value in checked if value is not _SKIP]
    if real:
        return real
    if pointed is not _SKIP:
        return [pointed]
    return []


def select_sentences(block: WordBlock) -> list[Sentence]:
    choices = []
    for sentence in block.sentences:
        title = (
            sentence.text
            if not sentence.note
            else f"{sentence.text}   ({sentence.note})"
        )
        choices.append(Choice(title, value=sentence))
    choices.append(Choice("✗ None (skip this word)", value=_SKIP))

    ic = InquirerControl(choices, None, pointer="❯", show_description=False)

    def get_tokens():
        return [
            ("class:question", " Select sentences "),
            (
                "class:instruction",
                "· space toggles · Enter confirms · empty Enter picks the arrowed one",
            ),
        ]

    layout = create_inquirer_layout(ic, get_tokens)
    bindings = KeyBindings()

    @bindings.add(Keys.ControlC, eager=True)
    @bindings.add(Keys.ControlQ, eager=True)
    def _abort(event):
        event.app.exit(exception=KeyboardInterrupt)

    @bindings.add(" ", eager=True)
    def _toggle(event):
        value = ic.get_pointed_at().value
        if value in ic.selected_options:
            ic.selected_options.remove(value)
        else:
            ic.selected_options.append(value)

    def _down(event):
        ic.select_next()
        while not ic.is_selection_valid():
            ic.select_next()

    def _up(event):
        ic.select_previous()
        while not ic.is_selection_valid():
            ic.select_previous()

    bindings.add(Keys.Down, eager=True)(_down)
    bindings.add(Keys.Up, eager=True)(_up)
    bindings.add("j", eager=True)(_down)
    bindings.add("k", eager=True)(_up)

    @bindings.add(Keys.ControlM, eager=True)
    def _confirm(event):
        checked = [choice.value for choice in ic.get_selected_values()]
        pointed = ic.get_pointed_at().value
        ic.is_answered = True
        event.app.exit(result=_resolve_selection(checked, pointed))

    @bindings.add(Keys.Any)
    def _ignore(event):
        pass

    app: Application = Application(
        layout=layout, key_bindings=bindings, style=merge_styles_default([])
    )
    return app.run()
