from __future__ import annotations

import html
import re
from dataclasses import dataclass

from .audio.base import speech_text
from .audio.recording import RecordingRun
from .cards import build_back, highlight_html
from .config import Config
from .models import ImportedCard, Sentence, WordBlock, parse_imported_text
from .tags import ORIGIN_TAG, RESERVED_TAGS, normalize_tag

NOTE_TYPE_NAME = "Sea Minerator"
FRONT_FIELD = "Front"
BACK_FIELD = "Back"
AUDIO_FIELD = "Audio"
LABEL_CLASS = "sm-label"
AUDIO_WARNING = "audio not recorded, system voice used: "
SAVE_WARNING = "recording not saved, system voice used: "

_LABEL_PREFIX = re.compile(r"^\s*\[([^\[\]]+)\]\s*(.*)$", re.DOTALL)


@dataclass
class CardResult:
    expression: str
    front: str
    created: bool
    note_id: int | None = None
    warning: str | None = None


def _exists(front: str, anki) -> bool:
    return anki.is_duplicate(NOTE_TYPE_NAME, {FRONT_FIELD: front})


def _audio_fields(
    run: RecordingRun | None, text: str, front: str, anki, warnings: list[str]
) -> dict[str, str]:
    # No run means the system voice: the Audio key is left out entirely, so
    # an old two-field note type keeps working without the field.
    if run is None:
        return {}
    # A duplicate is refused by add_note; saving its recording would leave an
    # unused file and warning about its audio would only add noise.
    if _exists(front, anki):
        return {}
    recording = run.recordings.get(text)
    if recording is None:
        reason = run.failures.get(text, "nothing to record")
        # A stopped run is explained once in the summary, not on every card.
        if reason != run.stopped:
            warnings.append(AUDIO_WARNING + reason)
        return {AUDIO_FIELD: ""}
    # Written before the note is added: the field must name the file Anki
    # actually stored. A note that still fails (a bad deck name) leaves an
    # unused file, which Check Media removes like any other.
    try:
        name = anki.write_media(recording.name, recording.data)
    except Exception as exc:
        # A full disk or a locked media folder costs this card its audio,
        # never the batch.
        warnings.append(f"{SAVE_WARNING}{exc}")
        return {AUDIO_FIELD: ""}
    return {AUDIO_FIELD: f"[sound:{name}]"}


def _add(
    expression: str,
    front: str,
    back: str,
    deck: str,
    anki,
    warnings: list[str],
    extra: dict[str, str],
):
    fields = {FRONT_FIELD: front, BACK_FIELD: back, **extra}
    try:
        note_id = anki.add_note(deck, NOTE_TYPE_NAME, fields, tags=[ORIGIN_TAG])
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
    word: WordBlock,
    sentence: Sentence,
    cfg: Config,
    deck: str,
    anki,
    run: RecordingRun | None = None,
) -> CardResult:
    warnings: list[str] = []
    front = _mined_front(sentence, cfg)
    if sentence.highlight and front == sentence.text:
        warnings.append(f"highlight '{sentence.highlight}' not found in sentence")
    back = build_back(word, sentence.topics)
    audio = _audio_fields(run, speech_text(sentence.text), front, anki, warnings)
    return _add(word.expression, front, back, deck, anki, warnings, audio)


def _mined_front(sentence: Sentence, cfg: Config) -> str:
    return highlight_html(sentence.text, sentence.highlight, cfg.highlight_color)


def create_cards_for_selection(
    word: WordBlock,
    selected: list[Sentence],
    cfg: Config,
    deck: str,
    anki,
    run: RecordingRun | None = None,
) -> list[CardResult]:
    return [create_card(word, s, cfg, deck, anki, run) for s in selected]


def mined_speech(
    pairs: list[tuple[WordBlock, list[Sentence]]], cfg: Config, anki
) -> list[str]:
    """The sentences to record: those whose card is not in the collection yet.

    A sentence mined before would only be refused as a duplicate, so
    recording it would spend a request (and Gemini quota) for nothing.
    """
    return [
        speech_text(s.text)
        for _word, sentences in pairs
        for s in sentences
        if not _exists(_mined_front(s, cfg), anki)
    ]


def imported_front(front: str) -> str:
    # A leading "[Grammar]" becomes an empty span the note type's CSS draws
    # as "[Grammar] ": it stays visible on the card but is not in the field's
    # text, so the {{tts}} audio reads only the sentence.
    match = _LABEL_PREFIX.match(front)
    if not match:
        return front
    label = html.escape(match.group(1), quote=True)
    return f'<span class="{LABEL_CLASS}" data-label="{label}"></span>{match.group(2)}'


def imported_back(back: str, topic: str) -> str:
    tag = normalize_tag(topic)
    if not tag or back.rstrip().endswith(f"({tag})"):
        return back
    return f"{back} ({tag})"


@dataclass(frozen=True)
class ImportPlan:
    cards: list[ImportedCard]
    warnings: list[str]
    topic: str  # normalized; "" when there is none


def prepare_import(text: str, topic: str) -> ImportPlan:
    cards, warnings = parse_imported_text(text)

    kept: list[ImportedCard] = []
    for card in cards:
        match = _LABEL_PREFIX.match(card.front)
        if match and not match.group(2).strip():
            # "[Grammar]" alone would become an empty note (Anki rejects it
            # as empty with a misleading "duplicate or empty" message).
            warnings.append(f"card '{card.front}' skipped: the front has only a label")
        else:
            kept.append(card)

    tag = normalize_tag(topic)
    if topic.strip() and not tag:
        warnings.append(
            f"topic '{topic.strip()}' ignored: use letters, digits and spaces"
        )
    elif tag in RESERVED_TAGS:
        warnings.append(f"topic '{tag}' ignored: it is a reserved tag")
        tag = ""
    return ImportPlan(cards=kept, warnings=warnings, topic=tag)


def create_imported_card(
    card: ImportedCard,
    cfg: Config,
    deck: str,
    anki,
    topic: str = "",
    run: RecordingRun | None = None,
) -> CardResult:
    warnings: list[str] = []
    front = imported_front(card.front)
    text = speech_text(card.front, strip_label=True)
    audio = _audio_fields(run, text, front, anki, warnings)
    back = imported_back(card.back, topic)
    return _add(card.front, front, back, deck, anki, warnings, audio)


def create_imported_cards(
    cards: list[ImportedCard],
    cfg: Config,
    deck: str,
    anki,
    topic: str = "",
    run: RecordingRun | None = None,
) -> list[CardResult]:
    return [create_imported_card(c, cfg, deck, anki, topic, run) for c in cards]


def imported_speech(cards: list[ImportedCard], anki) -> list[str]:
    """The fronts to record: those not in the collection yet (see mined_speech)."""
    return [
        speech_text(card.front, strip_label=True)
        for card in cards
        if not _exists(imported_front(card.front), anki)
    ]
