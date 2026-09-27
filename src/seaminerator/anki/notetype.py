from __future__ import annotations

from ..core.flow import BACK_FIELD, FRONT_FIELD, LABEL_CLASS, NOTE_TYPE_NAME

__all__ = [
    "BACK_FIELD",
    "FRONT_FIELD",
    "LABEL_CSS",
    "NOTE_TYPE_NAME",
    "ensure_notetype",
    "front_template",
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


def front_template(lang: str, voices: tuple[str, ...] = (), speed: float = 1.0) -> str:
    return f"{{{{{FRONT_FIELD}}}}}\n\n{tts_tag(lang, voices, speed)}"


def ensure_notetype(
    col, lang: str, voices: tuple[str, ...] = (), speed: float = 1.0
) -> int:
    wanted_front = front_template(lang, voices, speed)
    model = col.models.by_name(NOTE_TYPE_NAME)
    if model is None:
        model = _create(col, wanted_front)
        return model["id"]

    if _repair_fields(col, model):
        col.models.save(model)

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


def _repair_fields(col, model: dict) -> bool:
    """Restore field names/positions to (FRONT_FIELD, BACK_FIELD).

    Handles the two realistic drift shapes: the right number of fields with
    wrong names (renamed positionally back), and a missing field (added).
    Must run before any template comparison/rewrite, since a template can't
    be saved with a reference to a field that doesn't exist.
    """
    changed = False
    for index, name in enumerate((FRONT_FIELD, BACK_FIELD)):
        if index < len(model["flds"]):
            if model["flds"][index]["name"] != name:
                col.models.rename_field(model, model["flds"][index], name)
                changed = True
        else:
            col.models.add_field(model, col.models.new_field(name))
            changed = True
    return changed


def _create(col, front: str) -> dict:
    model = col.models.new(NOTE_TYPE_NAME)
    for name in (FRONT_FIELD, BACK_FIELD):
        col.models.add_field(model, col.models.new_field(name))
    template = col.models.new_template(TEMPLATE_NAME)
    template["qfmt"] = front
    template["afmt"] = BACK_TEMPLATE
    col.models.add_template(model, template)
    _add_label_css(model)
    col.models.add(model)
    return col.models.by_name(NOTE_TYPE_NAME)
