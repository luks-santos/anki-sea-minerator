from __future__ import annotations

from ..core.flow import BACK_FIELD, FRONT_FIELD, NOTE_TYPE_NAME

__all__ = [
    "BACK_FIELD",
    "FRONT_FIELD",
    "NOTE_TYPE_NAME",
    "ensure_notetype",
    "front_template",
    "tts_tag",
]

TEMPLATE_NAME = "Card 1"
BACK_TEMPLATE = "{{FrontSide}}\n\n<hr id=answer>\n\n{{Back}}"


def tts_tag(lang: str) -> str:
    return f"{{{{tts {lang}:text:{FRONT_FIELD}}}}}"


def front_template(lang: str) -> str:
    return f"{{{{{FRONT_FIELD}}}}}\n\n{tts_tag(lang)}"


def ensure_notetype(col, lang: str) -> int:
    model = col.models.by_name(NOTE_TYPE_NAME)
    if model is None:
        model = _create(col, lang)
        return model["id"]

    wanted_front = front_template(lang)
    template = model["tmpls"][0]
    if template["qfmt"] != wanted_front or template["afmt"] != BACK_TEMPLATE:
        template["qfmt"] = wanted_front
        template["afmt"] = BACK_TEMPLATE
        col.models.save(model)
    return model["id"]


def _create(col, lang: str) -> dict:
    model = col.models.new(NOTE_TYPE_NAME)
    for name in (FRONT_FIELD, BACK_FIELD):
        col.models.add_field(model, col.models.new_field(name))
    template = col.models.new_template(TEMPLATE_NAME)
    template["qfmt"] = front_template(lang)
    template["afmt"] = BACK_TEMPLATE
    col.models.add_template(model, template)
    col.models.add(model)
    return col.models.by_name(NOTE_TYPE_NAME)
