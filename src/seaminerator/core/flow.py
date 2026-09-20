from __future__ import annotations

from dataclasses import dataclass

from .cards import build_back, highlight_html
from .config import Config
from .models import ImportedCard, Sentence, WordBlock

NOTE_TYPE_NAME = "Sea Minerator"
FRONT_FIELD = "Front"
BACK_FIELD = "Back"
CARD_TAG = "anki-sea-minerator"


@dataclass
class CardResult:
    expression: str
    front: str
    created: bool
    note_id: int | None = None
    warning: str | None = None


def _add(expression: str, front: str, back: str, deck: str, anki, warnings: list[str]):
    fields = {FRONT_FIELD: front, BACK_FIELD: back}
    try:
        note_id = anki.add_note(deck, NOTE_TYPE_NAME, fields, tags=[CARD_TAG])
    except Exception as exc:
        warnings.append(f"card not created: {exc}")
        return CardResult(
            expression=expression,
            front=front,
            created=False,
            note_id=None,
            warning="; ".join(warnings),
        )
    return CardResult(
        expression=expression,
        front=front,
        created=True,
        note_id=note_id,
        warning="; ".join(warnings) if warnings else None,
    )


def create_card(
    word: WordBlock, sentence: Sentence, cfg: Config, deck: str, anki
) -> CardResult:
    warnings: list[str] = []
    front = highlight_html(sentence.text, sentence.highlight, cfg.highlight_color)
    if sentence.highlight and front == sentence.text:
        warnings.append(f"highlight '{sentence.highlight}' not found in sentence")
    return _add(word.expression, front, build_back(word), deck, anki, warnings)


def create_cards_for_selection(
    word: WordBlock, selected: list[Sentence], cfg: Config, deck: str, anki
) -> list[CardResult]:
    return [create_card(word, s, cfg, deck, anki) for s in selected]


def create_imported_card(
    card: ImportedCard, cfg: Config, deck: str, anki
) -> CardResult:
    return _add(card.front, card.front, card.back, deck, anki, [])


def create_imported_cards(
    cards: list[ImportedCard], cfg: Config, deck: str, anki
) -> list[CardResult]:
    return [create_imported_card(c, cfg, deck, anki) for c in cards]
