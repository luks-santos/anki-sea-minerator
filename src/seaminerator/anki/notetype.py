from __future__ import annotations

from ..core.flow import (
    AUDIO_FIELD,
    BACK_FIELD,
    FRONT_FIELD,
    LABEL_CLASS,
    NOTE_TYPE_NAME,
    TOPIC_FIELD,
)

__all__ = [
    "AUDIO_FIELD",
    "BACK_FIELD",
    "FRONT_FIELD",
    "LABEL_CSS",
    "NOTE_TYPE_NAME",
    "TOPIC_CSS",
    "TOPIC_FIELD",
    "ensure_notetype",
    "front_template",
    "has_audio_field",
    "has_topic_field",
    "tts_tag",
]

TEMPLATE_NAME = "Card 1"
BACK_TEMPLATE = "{{FrontSide}}\n\n<hr id=answer>\n\n{{Back}}"

# Draws an imported card's "[Grammar]" prefix from an empty span's
# data-label (see core.flow.imported_front): shown on the card, absent from
# the field text that {{tts}} reads aloud.
LABEL_CSS = f'.{LABEL_CLASS}::before {{ content: "[" attr(data-label) "] "; }}'

TOPIC_CLASS = "sm-topic"
# The Topic field drawn as a pill above the sentence; {{FrontSide}} repeats
# it on the back. A table box sizes to its text like inline-block but takes
# a line of its own, so the pill can't sit beside the sentence.
TOPIC_CSS = (
    f".{TOPIC_CLASS} {{ display: table; margin: 0 auto 0.5em; "
    "padding: 0.1em 0.7em; border-radius: 999px; font-size: 0.6em; "
    "font-weight: 600; color: #fff; background: #2563eb; }"
)


def tts_tag(lang: str, voices: tuple[str, ...] = (), speed: float = 1.0) -> str:
    # Default options are left out, so a note type made before voices could
    # be chosen isn't rewritten until the user actually picks one.
    options = [lang]
    if voices:
        options.append(f"voices={','.join(voices)}")
    if speed != 1.0:
        options.append(f"speed={speed:g}")
    return f"{{{{tts {' '.join(options)}:text:{FRONT_FIELD}}}}}"


def _tag(name: str) -> str:
    return "{{" + name + "}}"


def front_template(
    lang: str,
    voices: tuple[str, ...] = (),
    speed: float = 1.0,
    *,
    audio: bool = False,
    topic: bool = False,
) -> str:
    fallback = tts_tag(lang, voices, speed)
    # An empty Topic draws nothing, so a vocabulary card has no badge.
    t = TOPIC_FIELD
    badge = (
        f'{_tag("#" + t)}<div class="{TOPIC_CLASS}">{_tag(t)}</div>{_tag("/" + t)}\n'
        if topic
        else ""
    )
    if not audio:
        return f"{badge}{_tag(FRONT_FIELD)}\n\n{fallback}"
    # Plays the recording when the card has one, the system voice otherwise.
    a = AUDIO_FIELD
    return (
        f"{badge}{_tag(FRONT_FIELD)}\n\n"
        f"{_tag('#' + a)}{_tag(a)}{_tag('/' + a)}"
        f"{_tag('^' + a)}{fallback}{_tag('/' + a)}"
    )


def has_audio_field(col) -> bool:
    # True when the note type doesn't exist yet: creating it with the field
    # costs no full sync, so there is nothing to ask the user.
    model = col.models.by_name(NOTE_TYPE_NAME)
    return model is None or _has_field(model, AUDIO_FIELD)


def has_topic_field(col) -> bool:
    # Like has_audio_field: a note type yet to be created gets Topic for free.
    model = col.models.by_name(NOTE_TYPE_NAME)
    return model is None or _has_field(model, TOPIC_FIELD)


def _has_field(model: dict, name: str) -> bool:
    return any(field["name"] == name for field in model["flds"])


def ensure_notetype(
    col,
    lang: str,
    voices: tuple[str, ...] = (),
    speed: float = 1.0,
    *,
    audio: bool = False,
    topic: bool = False,
) -> int:
    model = col.models.by_name(NOTE_TYPE_NAME)
    if model is None:
        model = _create(col, lang, voices, speed)
        return model["id"]

    if _repair_fields(col, model, audio, topic):
        col.models.save(model)

    wanted_front = front_template(
        lang,
        voices,
        speed,
        audio=_has_field(model, AUDIO_FIELD),
        topic=_has_field(model, TOPIC_FIELD),
    )
    template = model["tmpls"][0]
    if template["qfmt"] != wanted_front or template["afmt"] != BACK_TEMPLATE:
        template["qfmt"] = wanted_front
        template["afmt"] = BACK_TEMPLATE
        col.models.save(model)

    if _add_styles(model):
        col.models.save(model)
    return model["id"]


def _add_styles(model: dict) -> bool:
    # Match on the selector, not the whole rule, so a user who restyles the
    # label or the badge keeps their version instead of getting ours again.
    # That makes a written rule final, so the badge's waits for its field.
    changed = False
    for selector, rule, wanted in (
        (f".{LABEL_CLASS}::before", LABEL_CSS, True),
        (f".{TOPIC_CLASS}", TOPIC_CSS, _has_field(model, TOPIC_FIELD)),
    ):
        if wanted and selector not in model["css"]:
            model["css"] = f"{model['css'].rstrip()}\n\n{rule}\n"
            changed = True
    return changed


def _repair_fields(col, model: dict, audio: bool, topic: bool = False) -> bool:
    """Restore the Front and Back fields, Front first, and Audio or Topic when asked.

    Fields are matched by name first, so a user who reorders them (moving
    Audio, or adding a field of their own) keeps every field and its content.
    Only a missing Front or Back is repaired: the field in its usual slot is
    renamed back when it isn't one of ours (a field renamed in place),
    otherwise a new one is added there. Front must come first, since Anki's
    duplicate and empty checks read the first field. Every one of these
    changes the schema (a full sync), which is why Audio and Topic are only
    added when `audio` or `topic` is set. Must run before any template
    comparison/rewrite, since a template can't be saved with a reference to a
    field that doesn't exist.
    """
    ours = (FRONT_FIELD, BACK_FIELD, AUDIO_FIELD, TOPIC_FIELD)
    changed = False
    for index, name in enumerate((FRONT_FIELD, BACK_FIELD)):
        if _has_field(model, name):
            continue
        fields = model["flds"]
        if index < len(fields) and fields[index]["name"] not in ours:
            col.models.rename_field(model, fields[index], name)
        else:
            field = col.models.new_field(name)
            col.models.add_field(model, field)
            col.models.reposition_field(model, field, index)
        changed = True
    front = next(f for f in model["flds"] if f["name"] == FRONT_FIELD)
    if model["flds"].index(front) != 0:
        col.models.reposition_field(model, front, 0)
        changed = True
    for wanted, name in ((audio, AUDIO_FIELD), (topic, TOPIC_FIELD)):
        if wanted and not _has_field(model, name):
            col.models.add_field(model, col.models.new_field(name))
            changed = True
    return changed


def _create(col, lang: str, voices: tuple[str, ...], speed: float) -> dict:
    # A new note type gets Audio and Topic from the start: adding a note
    # type, unlike adding a field to one, needs no full sync.
    model = col.models.new(NOTE_TYPE_NAME)
    for name in (FRONT_FIELD, BACK_FIELD, AUDIO_FIELD, TOPIC_FIELD):
        col.models.add_field(model, col.models.new_field(name))
    template = col.models.new_template(TEMPLATE_NAME)
    template["qfmt"] = front_template(lang, voices, speed, audio=True, topic=True)
    template["afmt"] = BACK_TEMPLATE
    col.models.add_template(model, template)
    _add_styles(model)
    col.models.add(model)
    return col.models.by_name(NOTE_TYPE_NAME)
