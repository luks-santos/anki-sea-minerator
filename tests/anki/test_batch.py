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

import pytest
from anki.errors import NotFoundError

from seaminerator.anki.batch import create_batch
from seaminerator.anki.notetype import ensure_notetype
from seaminerator.core.config import Config
from seaminerator.core.models import Sentence, WordBlock


def make_pair(expression: str, sentence_texts: list[str]):
    block = WordBlock(
        expression=expression,
        explanation="",
        translations=["x"],
        grammar_class="Noun",
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
