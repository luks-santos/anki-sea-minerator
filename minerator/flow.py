from __future__ import annotations

import base64
from dataclasses import dataclass

from minerator.cards import (
    audio_filename,
    build_back,
    build_front,
    highlight_html,
    strip_bracket_tag,
)
from minerator.config import Config
from minerator.models import ImportedCard, Sentence, WordBlock


@dataclass
class CardResult:
    expression: str
    front: str
    created: bool
    note_id: int | None = None
    warning: str | None = None


def create_card(
    word: WordBlock, sentence: Sentence, cfg: Config, deck: str, anki, tts
) -> CardResult:
    warnings: list[str] = []

    audio_file: str | None = None
    if tts is not None:
        try:
            data = tts.synthesize(sentence.text)
            audio_file = audio_filename(sentence.text)
            anki.store_media_file(audio_file, base64.b64encode(data).decode("ascii"))
        except Exception as exc:  # best-effort audio
            audio_file = None
            warnings.append(f"audio failed: {exc}")

    highlighted = highlight_html(sentence.text, sentence.highlight, cfg.highlight_color)
    if sentence.highlight and highlighted == sentence.text:
        warnings.append(f"highlight '{sentence.highlight}' not found in sentence")

    front = build_front(highlighted, audio_file)
    back = build_back(word)
    fields = {cfg.front_field: front, cfg.back_field: back}

    try:
        note_id = anki.add_note(
            deck, cfg.note_type, fields, tags=["anki-sea-minerator"]
        )
    except Exception as exc:
        warnings.append(f"card not created: {exc}")
        return CardResult(
            expression=word.expression,
            front=front,
            created=False,
            note_id=None,
            warning="; ".join(warnings),
        )

    return CardResult(
        expression=word.expression,
        front=front,
        created=True,
        note_id=note_id,
        warning="; ".join(warnings) if warnings else None,
    )


def create_cards_for_selection(
    word: WordBlock, selected: list[Sentence], cfg: Config, deck: str, anki, tts
) -> list[CardResult]:
    return [create_card(word, s, cfg, deck, anki, tts) for s in selected]


def create_imported_card(
    card: ImportedCard, cfg: Config, deck: str, anki, tts
) -> CardResult:
    warnings: list[str] = []

    tts_input = strip_bracket_tag(card.front) if cfg.strip_bracket_tags else card.front

    audio_file: str | None = None
    if tts is not None:
        try:
            data = tts.synthesize(tts_input)
            audio_file = audio_filename(tts_input)
            anki.store_media_file(audio_file, base64.b64encode(data).decode("ascii"))
        except Exception as exc:  # best-effort audio
            audio_file = None
            warnings.append(f"audio failed: {exc}")

    front = build_front(card.front, audio_file)
    back = card.back
    fields = {cfg.front_field: front, cfg.back_field: back}

    try:
        note_id = anki.add_note(
            deck, cfg.note_type, fields, tags=["anki-sea-minerator"]
        )
    except Exception as exc:
        warnings.append(f"card not created: {exc}")
        return CardResult(
            expression=card.front,
            front=front,
            created=False,
            note_id=None,
            warning="; ".join(warnings),
        )

    return CardResult(
        expression=card.front,
        front=front,
        created=True,
        note_id=note_id,
        warning="; ".join(warnings) if warnings else None,
    )


def create_imported_cards(
    cards: list[ImportedCard], cfg: Config, deck: str, anki, tts
) -> list[CardResult]:
    return [create_imported_card(c, cfg, deck, anki, tts) for c in cards]
