import pytest

from seaminerator.anki.notetype import LABEL_CSS, NOTE_TYPE_NAME, front_template


@pytest.fixture
def two_field_note_type(col):
    """The note type as versions before recorded audio made it, freshly synced.

    Holds one note. After this fixture, `col.schema_changed()` is falsy, so a
    test can tell whether a later step forced a full sync. It already has the
    label CSS, as those versions added it, so ensure_notetype has nothing
    else to save.
    """
    model = col.models.new(NOTE_TYPE_NAME)
    for name in ("Front", "Back"):
        col.models.add_field(model, col.models.new_field(name))
    template = col.models.new_template("Card 1")
    template["qfmt"] = front_template("en_US")
    template["afmt"] = "{{FrontSide}}\n\n<hr id=answer>\n\n{{Back}}"
    col.models.add_template(model, template)
    model["css"] = f"{model['css'].rstrip()}\n\n{LABEL_CSS}\n"
    col.models.add(model)
    note = col.new_note(col.models.by_name(NOTE_TYPE_NAME))
    note["Front"] = "Old card."
    note["Back"] = "Old back."
    col.add_note(note, col.decks.id("English"))
    col.db.execute("update col set ls = scm + 1")
    return note.id
