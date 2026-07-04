from __future__ import annotations

import typer
from rich.console import Console

from minerator.ai.gemini import GeminiConnector
from minerator.anki.client import AnkiClient
from minerator.cards import build_back
from minerator.config import Config, config_path, load_config, save_config
from minerator.flow import create_cards_for_selection
from minerator.prompt import DEFAULT_PROMPT, load_prompt
from minerator.tts.base import get_engine

app = typer.Typer(help="Mine English vocabulary into Anki flashcards.")
config_app = typer.Typer(help="Manage configuration.")
app.add_typer(config_app, name="config")
console = Console()


def _load() -> Config:
    return load_config(config_path())


@app.command()
def check() -> None:
    """Check AnkiConnect connectivity and API key presence."""
    cfg = _load()
    anki_ok = AnkiClient().ping()
    console.print(f"Anki (AnkiConnect): {'reachable' if anki_ok else 'NOT reachable'}")
    console.print(f"Gemini API key: {'set' if cfg.gemini_api_key else 'missing'}")


@config_app.command("show")
def config_show() -> None:
    """Show current configuration (API key masked)."""
    cfg = _load()
    for key, value in cfg.__dict__.items():
        if key == "gemini_api_key" and value:
            value = "***set***"
        console.print(f"{key} = {value}")


@config_app.command("edit-prompt")
def config_edit_prompt() -> None:
    """Ensure a prompt file exists and print its path for editing."""
    cfg = _load()
    from pathlib import Path

    path = Path(cfg.prompt_path) if cfg.prompt_path else config_path().parent / "prompt.txt"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_PROMPT, encoding="utf-8")
    if not cfg.prompt_path:
        # Load without the env-sourced API key so it never gets persisted to disk.
        file_cfg = load_config(config_path(), use_env=False)
        file_cfg.prompt_path = str(path)
        save_config(file_cfg, config_path())
    console.print(f"Edit your prompt at: {path}")


def _read_words() -> list[str]:
    console.print("Paste your list of the day (one per line, empty line to finish):")
    words: list[str] = []
    while True:
        try:
            line = input().strip()
        except EOFError:
            break
        if not line:
            break
        words.append(line)
    return words


@app.command()
def mine() -> None:
    """Run an interactive mining session."""
    import questionary

    cfg = _load()
    if not cfg.gemini_api_key:
        console.print("[red]No Gemini API key configured.[/red]")
        raise typer.Exit(1)

    anki = AnkiClient()
    if not anki.ping():
        console.print("[red]AnkiConnect not reachable. Open Anki with the add-on.[/red]")
        raise typer.Exit(1)

    if cfg.note_type not in anki.model_names():
        console.print(f"[red]Note type '{cfg.note_type}' not found in Anki.[/red]")
        raise typer.Exit(1)
    note_fields = anki.model_field_names(cfg.note_type)
    missing_fields = [f for f in (cfg.front_field, cfg.back_field) if f not in note_fields]
    if missing_fields:
        console.print(
            f"[red]Field(s) {', '.join(missing_fields)} not found in note type "
            f"'{cfg.note_type}'.[/red]"
        )
        raise typer.Exit(1)

    words = _read_words()
    if not words:
        console.print("Nothing to mine.")
        raise typer.Exit(0)

    decks = anki.deck_names()
    deck = questionary.select(
        "Target deck:", choices=decks,
        default=cfg.default_deck if cfg.default_deck in decks else None,
    ).ask()
    if deck is None:
        console.print("Cancelled.")
        raise typer.Exit(0)

    try:
        tts = get_engine(cfg.tts_engine, cfg.tts_voice)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    connector = GeminiConnector(cfg.gemini_api_key, cfg.model)
    try:
        blocks = connector.mine(words, load_prompt(cfg.prompt_path))
    except Exception as exc:
        console.print(f"[red]Failed to mine words: {exc}[/red]")
        raise typer.Exit(1)

    total_created = 0
    for block in blocks:
        console.print(f"\n[bold]{block.expression}[/bold] — {block.explanation}")
        console.print(build_back(block))
        if not block.sentences:
            console.print(f"[yellow]! no sentences returned for '{block.expression}'[/yellow]")
            continue
        choices = [
            questionary.Choice(title=f"{s.text}  ({s.note})", value=s) for s in block.sentences
        ]
        selected = questionary.checkbox("Select sentences:", choices=choices).ask() or []
        for res in create_cards_for_selection(block, selected, cfg, deck, anki, tts):
            total_created += 1 if res.created else 0
            if res.warning:
                console.print(f"[yellow]! {res.warning}[/yellow]")

    console.print(f"\n[green]Done. Cards created: {total_created}[/green]")
