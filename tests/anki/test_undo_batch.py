"""Verifies the wizard's undo-batching assumption against a real collection.

The wizard wraps a whole batch of card creations in a single CollectionOp,
opening a custom undo entry before creating any notes and merging every
undo step generated along the way into it. This is the one assumption the
plan's spec flagged as unverified: that pairing `add_custom_undo_entry` with
`merge_undo_entries` really produces ONE undo entry that removes every
created note at once, rather than one entry per note. `aqt` is not involved
here -- `add_custom_undo_entry`, `merge_undo_entries`, `undo`, `undo_name`
and `undo_status` are plain `anki.collection.Collection` (pylib) methods, so
the behavior is directly testable against the `col` fixture.

Ordering matters and is NOT the ordering the plan's spec sketch used. These
tests open the custom entry with `add_custom_undo_entry` BEFORE creating any
note, then call `merge_undo_entries(target)` AFTER the batch. Confirmed by
hand against a real Collection (anki 26.9.2): calling `add_custom_undo_entry`
AFTER the batch instead -- i.e. `merge_undo_entries(add_custom_undo_entry(...))`
evaluated once all notes already exist, as the spec sketch wrote it -- opens
a new, empty entry that is already the latest step, so merging "from target
to now" merges only that empty entry with itself. The first `undo()` then
removes nothing, and each note has to be undone one at a time. `wizard.py`
was written with the entry opened first for this reason.
"""

import pytest
from anki.errors import NotFoundError

from seaminerator.anki.collection_client import CollectionAnkiClient
from seaminerator.anki.notetype import NOTE_TYPE_NAME, ensure_notetype


def test_merged_undo_entry_removes_every_note_created_in_the_batch(col):
    ensure_notetype(col, "en_US")
    client = CollectionAnkiClient(col)

    target = col.add_custom_undo_entry("Mine vocabulary")
    note_ids = [
        client.add_note(
            deck="English",
            model=NOTE_TYPE_NAME,
            fields={"Front": front, "Back": "back"},
        )
        for front in ("one", "two", "three")
    ]
    col.merge_undo_entries(target)

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
    client = CollectionAnkiClient(col)

    target = col.add_custom_undo_entry("Mine vocabulary")
    for front in ("alpha", "beta", "gamma", "delta"):
        client.add_note(
            deck="English",
            model=NOTE_TYPE_NAME,
            fields={"Front": front, "Back": "back"},
        )
    col.merge_undo_entries(target)
    assert col.note_count() == 4

    col.undo()

    # A single undo either removes all four (merge worked) or leaves some
    # behind (merge failed and each add_note kept its own undo step). The
    # requirement is one undo for the whole batch, so this must be 0.
    assert col.note_count() == 0
