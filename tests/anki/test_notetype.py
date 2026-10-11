from seaminerator.anki.notetype import (
    AUDIO_FIELD,
    BACK_FIELD,
    FRONT_FIELD,
    LABEL_CSS,
    NOTE_TYPE_NAME,
    ensure_notetype,
    front_template,
    has_audio_field,
    tts_tag,
)


def test_tts_tag_uses_text_prefix_to_strip_html():
    assert tts_tag("en_US") == "{{tts en_US:text:Front}}"


def test_tts_tag_lists_the_chosen_voices_in_order_and_the_speed():
    assert (
        tts_tag("en_US", ("Microsoft_Zira", "Apple_Samantha"), 0.9)
        == "{{tts en_US voices=Microsoft_Zira,Apple_Samantha speed=0.9:text:Front}}"
    )


def test_tts_tag_leaves_out_default_options():
    assert tts_tag("en_US", (), 1.0) == "{{tts en_US:text:Front}}"
    assert tts_tag("en_US", (), 1.25) == "{{tts en_US speed=1.25:text:Front}}"
    assert (
        tts_tag("en_US", ("Microsoft_Zira",), 1.0)
        == "{{tts en_US voices=Microsoft_Zira:text:Front}}"
    )


def test_ensure_notetype_creates_it_with_three_fields(col):
    ensure_notetype(col, "en_US")

    model = col.models.by_name(NOTE_TYPE_NAME)
    assert model is not None
    assert [f["name"] for f in model["flds"]] == [FRONT_FIELD, BACK_FIELD, AUDIO_FIELD]


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


def test_ensure_notetype_rewrites_the_template_when_the_voice_changes(col):
    ensure_notetype(col, "en_US")
    ensure_notetype(col, "en_US", ("Microsoft_Zira",), 0.8)

    front = col.models.by_name(NOTE_TYPE_NAME)["tmpls"][0]["qfmt"]
    assert "{{tts en_US voices=Microsoft_Zira speed=0.8:text:Front}}" in front


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
    assert [f["name"] for f in model["flds"]] == [FRONT_FIELD, BACK_FIELD, AUDIO_FIELD]


def test_ensure_notetype_restores_a_missing_field(col):
    ensure_notetype(col, "en_US")
    model = col.models.by_name(NOTE_TYPE_NAME)
    col.models.remove_field(model, model["flds"][1])
    col.models.save(model)

    ensure_notetype(col, "en_US")

    model = col.models.by_name(NOTE_TYPE_NAME)
    assert [f["name"] for f in model["flds"]] == [FRONT_FIELD, BACK_FIELD, AUDIO_FIELD]


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


AUDIO_TEMPLATE = (
    "{{Front}}\n\n{{#Audio}}{{Audio}}{{/Audio}}"
    "{{^Audio}}{{tts en_US:text:Front}}{{/Audio}}"
)


def test_front_template_with_audio_falls_back_to_tts():
    assert front_template("en_US", audio=True) == AUDIO_TEMPLATE
    assert front_template("en_US") == "{{Front}}\n\n{{tts en_US:text:Front}}"


def test_a_new_note_type_gets_the_audio_template(col):
    ensure_notetype(col, "en_US")

    assert col.models.by_name(NOTE_TYPE_NAME)["tmpls"][0]["qfmt"] == AUDIO_TEMPLATE


def test_ensure_notetype_leaves_a_two_field_note_type_alone_without_audio(
    col, two_field_note_type
):
    ensure_notetype(col, "en_US")

    model = col.models.by_name(NOTE_TYPE_NAME)
    assert [f["name"] for f in model["flds"]] == [FRONT_FIELD, BACK_FIELD]
    assert model["tmpls"][0]["qfmt"] == front_template("en_US")
    assert not col.schema_changed()


def test_ensure_notetype_adds_the_audio_field_when_asked(col, two_field_note_type):
    ensure_notetype(col, "en_US", audio=True)

    model = col.models.by_name(NOTE_TYPE_NAME)
    assert [f["name"] for f in model["flds"]] == [FRONT_FIELD, BACK_FIELD, AUDIO_FIELD]
    assert model["tmpls"][0]["qfmt"] == AUDIO_TEMPLATE
    note = col.get_note(two_field_note_type)
    assert (note[FRONT_FIELD], note[AUDIO_FIELD]) == ("Old card.", "")


def test_ensure_notetype_keeps_the_audio_field_without_audio(col):
    ensure_notetype(col, "en_US", audio=True)

    ensure_notetype(col, "en_US")

    model = col.models.by_name(NOTE_TYPE_NAME)
    assert [f["name"] for f in model["flds"]] == [FRONT_FIELD, BACK_FIELD, AUDIO_FIELD]
    assert model["tmpls"][0]["qfmt"] == AUDIO_TEMPLATE


def test_has_audio_field(col, two_field_note_type):
    assert has_audio_field(col) is False

    ensure_notetype(col, "en_US", audio=True)

    assert has_audio_field(col) is True


def test_has_audio_field_is_true_before_the_note_type_exists(col):
    assert has_audio_field(col) is True


def _three_field_note_with_content(col):
    ensure_notetype(col, "en_US", audio=True)
    note = col.new_note(col.models.by_name(NOTE_TYPE_NAME))
    note[FRONT_FIELD] = "Kept front."
    note[BACK_FIELD] = "Kept back."
    col.add_note(note, col.decks.id("English"))
    return note.id


def _move_field(col, name, index):
    model = col.models.by_name(NOTE_TYPE_NAME)
    field = next(f for f in model["flds"] if f["name"] == name)
    col.models.reposition_field(model, field, index)
    col.models.save(model)
    col.db.execute("update col set ls = scm + 1")


def _names(col):
    return [f["name"] for f in col.models.by_name(NOTE_TYPE_NAME)["flds"]]


def test_ensure_notetype_keeps_an_audio_field_moved_between_front_and_back(col):
    note_id = _three_field_note_with_content(col)
    _move_field(col, AUDIO_FIELD, 1)

    ensure_notetype(col, "en_US")

    assert _names(col) == [FRONT_FIELD, AUDIO_FIELD, BACK_FIELD]
    note = col.get_note(note_id)
    assert (note[FRONT_FIELD], note[BACK_FIELD]) == ("Kept front.", "Kept back.")
    assert not col.schema_changed()


def test_ensure_notetype_puts_front_first_again_without_losing_content(col):
    note_id = _three_field_note_with_content(col)
    _move_field(col, AUDIO_FIELD, 0)

    ensure_notetype(col, "en_US")

    names = _names(col)
    assert names[0] == FRONT_FIELD
    assert sorted(names) == sorted([FRONT_FIELD, BACK_FIELD, AUDIO_FIELD])
    note = col.get_note(note_id)
    assert (note[FRONT_FIELD], note[BACK_FIELD]) == ("Kept front.", "Kept back.")


def test_ensure_notetype_keeps_a_field_the_user_added_between_front_and_back(col):
    ensure_notetype(col, "en_US")
    model = col.models.by_name(NOTE_TYPE_NAME)
    notes = col.models.new_field("Notes")
    col.models.add_field(model, notes)
    col.models.reposition_field(model, notes, 1)
    col.models.save(model)

    ensure_notetype(col, "en_US")

    assert _names(col) == [FRONT_FIELD, "Notes", BACK_FIELD, AUDIO_FIELD]
