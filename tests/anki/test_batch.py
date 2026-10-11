"""Verifies the wizard's undo-batching assumption against a real collection.

`create_batch` (src/seaminerator/anki/batch.py) is the pure-pylib function
the wizard's `CollectionOp` calls to create a whole batch of cards as one
undoable unit. It is the one assumption the plan's spec flagged as
unverified: that pairing `add_custom_undo_entry` with `merge_undo_entries`
really produces ONE undo entry that removes every created note at once,
rather than one entry per note. `aqt` is not involved here --
`add_custom_undo_entry`, `merge_undo_entries`, `undo`, `undo_name` and
`undo_status` are plain `anki.collection.Collection` (pylib) methods, and
neither `batch.py` nor this test imports `aqt`, so the behavior is directly
testable against the `col` fixture.

These tests call `create_batch` itself rather than re-implementing its
body, so they exercise the exact sequence the wizard runs. Confirmed by
hand against a real Collection (anki 26.9.2): opening the custom entry
*after* the loop instead of before -- i.e. calling
`merge_undo_entries(add_custom_undo_entry(...))` only once all notes
already exist -- opens a new, empty entry that is already the latest step,
so merging "from target to now" merges only that empty entry with itself.
The first `undo()` then removes nothing, and each note has to be undone one
at a time. `create_batch` opens the entry first for this reason, and
swapping the two lines in `batch.py` makes these tests fail (verified by
hand as part of this task; see the task report for the before/after run).
"""

from pathlib import Path

import pytest
from anki.errors import NotFoundError

from seaminerator.anki.batch import create_batch, create_import_batch
from seaminerator.anki.notetype import ensure_notetype
from seaminerator.core.audio.base import media_name
from seaminerator.core.audio.recording import Recording, RecordingRun
from seaminerator.core.config import Config
from seaminerator.core.models import ImportedCard, Sentence, WordBlock


def make_pair(expression: str, sentence_texts: list[str]):
    block = WordBlock(
        expression=expression,
        explanation="",
        translations=["x"],
        class_tag="noun",
        sentences=[],
    )
    sentences = [Sentence(text=text, highlight=expression) for text in sentence_texts]
    return block, sentences


def test_merged_undo_entry_removes_every_note_created_in_the_batch(col):
    ensure_notetype(col, "en_US")
    pairs = [
        make_pair("one", ["one."]),
        make_pair("two", ["two."]),
        make_pair("three", ["three."]),
    ]

    results, _changes = create_batch(col, pairs, Config(), "English")

    assert len(results) == 3
    assert all(r.created for r in results)
    note_ids = [r.note_id for r in results]
    assert col.note_count() == 3
    assert col.undo_status().undo == "Mine vocabulary"

    col.undo()

    assert col.note_count() == 0
    for note_id in note_ids:
        with pytest.raises(NotFoundError):
            col.get_note(note_id)
    assert col.undo_status().undo != "Mine vocabulary"


def test_a_single_undo_after_merge_does_not_leave_a_partial_batch(col):
    """One undo() call must remove the whole batch, not the last note only."""
    ensure_notetype(col, "en_US")
    pairs = [
        make_pair("alpha", ["alpha."]),
        make_pair("beta", ["beta."]),
        make_pair("gamma", ["gamma."]),
        make_pair("delta", ["delta."]),
    ]

    results, _changes = create_batch(col, pairs, Config(), "English")
    assert col.note_count() == 4
    assert all(r.created for r in results)

    col.undo()

    # A single undo either removes all four (merge worked) or leaves some
    # behind (merge failed and each add_note kept its own undo step). The
    # requirement is one undo for the whole batch, so this must be 0.
    assert col.note_count() == 0


def test_import_batch_creates_every_card_and_undoes_as_one(col):
    ensure_notetype(col, "en_US")
    cards = [
        ImportedCard(front="[Grammar] I've just arrived.", back="Eu acabei de chegar."),
        ImportedCard(front="[Grammar] Have you seen him?", back="Você viu ele?"),
    ]

    results, _changes = create_import_batch(
        col, cards, Config(), "Grammar", "present perfect"
    )

    assert [r.created for r in results] == [True, True]
    note = col.get_note(results[0].note_id)
    assert note["Back"] == "Eu acabei de chegar. (present-perfect)"
    assert col.undo_status().undo == "Import cards"

    col.undo()

    assert col.note_count() == 0


def recorded(*texts):
    return RecordingRun(
        recordings={
            text: Recording(media_name("google", "us", text), b"ID3" + text.encode())
            for text in texts
        }
    )


def test_batch_puts_each_recording_in_media_and_the_audio_field(col):
    ensure_notetype(col, "en_US", audio=True)
    pairs = [make_pair("one", ["one."]), make_pair("two", ["two."])]

    results, _changes = create_batch(
        col, pairs, Config(), "English", recorded("one.", "two.")
    )

    name = media_name("google", "us", "one.")
    note = col.get_note(results[0].note_id)
    assert note["Audio"] == f"[sound:{name}]"
    assert (Path(col.media.dir()) / name).read_bytes() == b"ID3one."
    assert results[0].warning is None
    col.undo()
    assert col.note_count() == 0


def test_batch_leaves_audio_empty_and_warns_when_a_recording_failed(col):
    ensure_notetype(col, "en_US", audio=True)
    run = RecordingRun(failures={"one.": "longer than 100 characters"})

    results, _changes = create_batch(
        col, [make_pair("one", ["one."])], Config(), "English", run
    )

    assert col.get_note(results[0].note_id)["Audio"] == ""
    assert results[0].warning == (
        "audio not recorded, system voice used: longer than 100 characters"
    )


def test_batch_does_not_repeat_the_stop_reason_on_every_card(col):
    ensure_notetype(col, "en_US", audio=True)
    run = RecordingRun(failures={"one.": "down", "two.": "down"}, stopped="down")
    pairs = [make_pair("one", ["one."]), make_pair("two", ["two."])]

    results, _changes = create_batch(col, pairs, Config(), "English", run)

    assert [r.created for r in results] == [True, True]
    assert [r.warning for r in results] == [None, None]


def test_a_repeated_sentence_keeps_the_first_card_and_its_recording(col):
    # Anki compares fronts without their HTML, so the same sentence with a
    # different highlight is still a duplicate; record_all records it once.
    ensure_notetype(col, "en_US", audio=True)
    pairs = [make_pair("see", ["I see one."]), make_pair("one", ["I see one."])]

    results, _changes = create_batch(
        col, pairs, Config(), "English", recorded("I see one.")
    )

    assert [r.created for r in results] == [True, False]
    assert "already exists" in results[1].warning
    sound = f"[sound:{media_name('google', 'us', 'I see one.')}]"
    assert col.get_note(results[0].note_id)["Audio"] == sound


def test_batch_without_a_run_works_on_a_two_field_note_type(col, two_field_note_type):
    ensure_notetype(col, "en_US")

    results, _changes = create_batch(
        col, [make_pair("one", ["one."])], Config(), "English"
    )

    assert results[0].created
    assert "Audio" not in col.get_note(results[0].note_id).keys()
    assert not col.schema_changed()


def test_import_batch_records_the_front_without_its_label(col):
    ensure_notetype(col, "en_US", audio=True)
    text = "I've just arrived."
    cards = [ImportedCard(front=f"[Grammar] {text}", back="Eu acabei de chegar.")]

    results, _changes = create_import_batch(
        col, cards, Config(), "Grammar", "", recorded(text)
    )

    note = col.get_note(results[0].note_id)
    assert note["Audio"] == f"[sound:{media_name('google', 'us', text)}]"
