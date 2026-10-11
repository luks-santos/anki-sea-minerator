from __future__ import annotations

from ..core.flow import (
    AUDIO_FIELD,
    BACK_FIELD,
    FRONT_FIELD,
    LABEL_CLASS,
    NOTE_TYPE_NAME,
)

__all__ = [
    "AUDIO_FIELD",
    "BACK_FIELD",
    "FRONT_FIELD",
    "LABEL_CSS",
    "NOTE_TYPE_NAME",
    "ensure_notetype",
    "front_template",
    "has_audio_field",
    "tts_tag",
]

TEMPLATE_NAME = "Card 1"
BACK_TEMPLATE = "{{FrontSide}}\n\n<hr id=answer>\n\n{{Back}}"

# Draws an imported card's "[Grammar]" prefix from an empty span's
# data-label (see core.flow.imported_front): shown on the card, absent from
# the field text that {{tts}} reads aloud.
LABEL_CSS = f'.{LABEL_CLASS}::before {{ content: "[" attr(data-label) "] "; }}'


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
) -> str:
    fallback = tts_tag(lang, voices, speed)
    if not audio:
        return f"{_tag(FRONT_FIELD)}\n\n{fallback}"
    # Plays the recording when the card has one, the system voice otherwise.
    a = AUDIO_FIELD
    return (
        f"{_tag(FRONT_FIELD)}\n\n"
        f"{_tag('#' + a)}{_tag(a)}{_tag('/' + a)}"
        f"{_tag('^' + a)}{fallback}{_tag('/' + a)}"
    )


def has_audio_field(col) -> bool:
    # True when the note type doesn't exist yet: creating it with the field
    # costs no full sync, so there is nothing to ask the user.
    model = col.models.by_name(NOTE_TYPE_NAME)
    return model is None or _has_field(model, AUDIO_FIELD)


def _has_field(model: dict, name: str) -> bool:
    return any(field["name"] == name for field in model["flds"])


def ensure_notetype(
    col,
    lang: str,
    voices: tuple[str, ...] = (),
    speed: float = 1.0,
    *,
    audio: bool = False,
) -> int:
    model = col.models.by_name(NOTE_TYPE_NAME)
    if model is None:
        model = _create(col, lang, voices, speed)
        return model["id"]

    if _repair_fields(col, model, audio):
        col.models.save(model)

    wanted_front = front_template(
        lang, voices, speed, audio=_has_field(model, AUDIO_FIELD)
    )
    template = model["tmpls"][0]
    if template["qfmt"] != wanted_front or template["afmt"] != BACK_TEMPLATE:
        template["qfmt"] = wanted_front
        template["afmt"] = BACK_TEMPLATE
        col.models.save(model)

    if _add_label_css(model):
        col.models.save(model)
    return model["id"]


def _add_label_css(model: dict) -> bool:
    # Match on the selector, not the whole rule, so a user who restyles the
    # label keeps their version instead of getting ours appended again.
    if f".{LABEL_CLASS}::before" in model["css"]:
        return False
    model["css"] = f"{model['css'].rstrip()}\n\n{LABEL_CSS}\n"
    return True


def _repair_fields(col, model: dict, audio: bool) -> bool:
    """Restore Front and Back at positions 0 and 1, and Audio when asked.

    Front/Back drift is repaired by position (a renamed field gets its name
    back, a missing one is added in place). Audio is matched by name and
    never renamed, so its recordings survive. Adding a field changes the
    schema (a full sync), which is why Audio is only added when `audio` is
    set. Must run before any template comparison/rewrite, since a template
    can't be saved with a reference to a field that doesn't exist.
    """
    changed = False
    for index, name in enumerate((FRONT_FIELD, BACK_FIELD)):
        fields = model["flds"]
        if index < len(fields) and fields[index]["name"] == name:
            continue
        if index < len(fields) and fields[index]["name"] != AUDIO_FIELD:
            col.models.rename_field(model, fields[index], name)
        else:
            field = col.models.new_field(name)
            col.models.add_field(model, field)
            col.models.reposition_field(model, field, index)
        changed = True
    if audio and not _has_field(model, AUDIO_FIELD):
        col.models.add_field(model, col.models.new_field(AUDIO_FIELD))
        changed = True
    return changed


def _create(col, lang: str, voices: tuple[str, ...], speed: float) -> dict:
    # A new note type gets Audio from the start: adding a note type, unlike
    # adding a field to one, needs no full sync.
    model = col.models.new(NOTE_TYPE_NAME)
    for name in (FRONT_FIELD, BACK_FIELD, AUDIO_FIELD):
        col.models.add_field(model, col.models.new_field(name))
    template = col.models.new_template(TEMPLATE_NAME)
    template["qfmt"] = front_template(lang, voices, speed, audio=True)
    template["afmt"] = BACK_TEMPLATE
    col.models.add_template(model, template)
    _add_label_css(model)
    col.models.add(model)
    return col.models.by_name(NOTE_TYPE_NAME)
