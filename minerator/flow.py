from __future__ import annotations

import base64
from dataclasses import dataclass

from minerator.cards import audio_filename, build_back, build_front, highlight_html
from minerator.config import Config
from minerator.models import Sentence, WordBlock


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

    if sentence.highlight and highlight_html(
        sentence.text, sentence.highlight, cfg.highlight_color
    ) == sentence.text:
        warnings.append(f"highlight '{sentence.highlight}' not found in sentence")

    front = build_front(sentence.text, sentence.highlight, cfg.highlight_color, audio_file)
    back = build_back(word)
    fields = {cfg.front_field: front, cfg.back_field: back}
    note_id = anki.add_note(deck, cfg.note_type, fields, tags=["anki-sea-minerator"])

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
