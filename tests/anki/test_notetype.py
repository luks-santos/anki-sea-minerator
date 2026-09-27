from seaminerator.anki.notetype import (
    BACK_FIELD,
    FRONT_FIELD,
    LABEL_CSS,
    NOTE_TYPE_NAME,
    ensure_notetype,
    tts_tag,
)


def test_tts_tag_uses_text_prefix_to_strip_html():
    assert tts_tag("en_US") == "{{tts en_US:text:Front}}"


def test_ensure_notetype_creates_it_with_both_fields(col):
    ensure_notetype(col, "en_US")

    model = col.models.by_name(NOTE_TYPE_NAME)
    assert model is not None
    assert [f["name"] for f in model["flds"]] == [FRONT_FIELD, BACK_FIELD]


def test_ensure_notetype_puts_the_tts_tag_in_the_front_template(col):
    ensure_notetype(col, "en_US")

    model = col.models.by_name(NOTE_TYPE_NAME)
    front = model["tmpls"][0]["qfmt"]
    assert "{{Front}}" in front
    assert "{{tts en_US:text:Front}}" in front


def test_ensure_notetype_back_template_shows_front_and_back(col):
    ensure_notetype(col, "en_US")

    back = col.models.by_name(NOTE_TYPE_NAME)["tmpls"][0]["afmt"]
    assert "{{FrontSide}}" in back
    assert "{{Back}}" in back


def test_ensure_notetype_is_idempotent(col):
    first = ensure_notetype(col, "en_US")
    second = ensure_notetype(col, "en_US")

    assert first == second
    assert (
        len([n for n in col.models.all_names_and_ids() if n.name == NOTE_TYPE_NAME])
        == 1
    )


def test_ensure_notetype_rewrites_the_template_when_the_language_changes(col):
    ensure_notetype(col, "en_US")
    ensure_notetype(col, "pt_BR")

    front = col.models.by_name(NOTE_TYPE_NAME)["tmpls"][0]["qfmt"]
    assert "{{tts pt_BR:text:Front}}" in front
    assert "en_US" not in front


def test_ensure_notetype_restores_a_stripped_tts_tag(col):
    ensure_notetype(col, "en_US")
    model = col.models.by_name(NOTE_TYPE_NAME)
    model["tmpls"][0]["qfmt"] = "{{Front}}"
    col.models.save(model)

    ensure_notetype(col, "en_US")

    front = col.models.by_name(NOTE_TYPE_NAME)["tmpls"][0]["qfmt"]
    assert "{{tts en_US:text:Front}}" in front


def test_ensure_notetype_restores_a_renamed_field(col):
    ensure_notetype(col, "en_US")
    model = col.models.by_name(NOTE_TYPE_NAME)
    col.models.rename_field(model, model["flds"][0], "Frente")
    col.models.save(model)

    ensure_notetype(col, "en_US")

    model = col.models.by_name(NOTE_TYPE_NAME)
    assert [f["name"] for f in model["flds"]] == [FRONT_FIELD, BACK_FIELD]


def test_ensure_notetype_restores_a_missing_field(col):
    ensure_notetype(col, "en_US")
    model = col.models.by_name(NOTE_TYPE_NAME)
    col.models.remove_field(model, model["flds"][1])
    col.models.save(model)

    ensure_notetype(col, "en_US")

    model = col.models.by_name(NOTE_TYPE_NAME)
    assert [f["name"] for f in model["flds"]] == [FRONT_FIELD, BACK_FIELD]


def test_ensure_notetype_is_usable_after_field_drift_is_repaired(col):
    ensure_notetype(col, "en_US")
    model = col.models.by_name(NOTE_TYPE_NAME)
    col.models.rename_field(model, model["flds"][0], "Frente")
    col.models.save(model)

    ensure_notetype(col, "en_US")

    model = col.models.by_name(NOTE_TYPE_NAME)
    note = col.new_note(model)
    note[FRONT_FIELD] = "hello"
    note[BACK_FIELD] = "world"
    col.add_note(note, col.decks.selected())

    saved = col.get_note(note.id)
    assert saved[FRONT_FIELD] == "hello"
    assert saved[BACK_FIELD] == "world"


def test_ensure_notetype_styles_the_imported_label(col):
    ensure_notetype(col, "en_US")

    css = col.models.by_name(NOTE_TYPE_NAME)["css"]
    assert LABEL_CSS in css


def test_ensure_notetype_adds_the_label_style_once(col):
    ensure_notetype(col, "en_US")
    ensure_notetype(col, "en_US")

    assert col.models.by_name(NOTE_TYPE_NAME)["css"].count(LABEL_CSS) == 1


def test_ensure_notetype_adds_the_label_style_to_an_existing_note_type(col):
    ensure_notetype(col, "en_US")
    model = col.models.by_name(NOTE_TYPE_NAME)
    model["css"] = ".card { color: black; }"
    col.models.save(model)

    ensure_notetype(col, "en_US")

    css = col.models.by_name(NOTE_TYPE_NAME)["css"]
    assert css.startswith(".card { color: black; }")
    assert LABEL_CSS in css


def test_ensure_notetype_keeps_a_user_edited_label_rule(col):
    ensure_notetype(col, "en_US")
    model = col.models.by_name(NOTE_TYPE_NAME)
    model["css"] = '.sm-label::before { content: attr(data-label) ": "; }'
    col.models.save(model)

    ensure_notetype(col, "en_US")

    css = col.models.by_name(NOTE_TYPE_NAME)["css"]
    assert css == '.sm-label::before { content: attr(data-label) ": "; }'
