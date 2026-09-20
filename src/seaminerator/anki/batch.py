from __future__ import annotations

from ..core.config import Config
from ..core.flow import CardResult, create_cards_for_selection
from ..core.models import Sentence, WordBlock
from .collection_client import CollectionAnkiClient

UNDO_NAME = "Mine vocabulary"


def create_batch(
    col,
    pairs: list[tuple[WordBlock, list[Sentence]]],
    cfg: Config,
    deck: str,
) -> tuple[list[CardResult], object]:
    """Create every selected card as one undo-batched unit.

    Opens a custom undo entry *before* creating any note and merges every
    undo step generated while creating the batch into it *after* the loop,
    so a single `col.undo()` removes every card created here at once.

    The order matters: `col.merge_undo_entries(target)` merges everything
    from `target` up to the current step into one entry. Opening the entry
    after the loop instead would make it the *latest* step already, so the
    merge would fold only that empty trailing entry into itself and leave
    one "Add Note" undo step per card. Reordering the two lines below
    reintroduces that bug -- see tests/anki/test_batch.py, which calls this
    function directly and fails if the order is wrong.

    Returns the per-card results plus whatever `col.merge_undo_entries`
    returns (an `OpChanges`), so a caller running this inside a
    `CollectionOp` can hand that value straight back as the op's result.
    """
    client = CollectionAnkiClient(col)
    target = col.add_custom_undo_entry(UNDO_NAME)
    results: list[CardResult] = []
    for word, sentences in pairs:
        results.extend(create_cards_for_selection(word, sentences, cfg, deck, client))
    changes = col.merge_undo_entries(target)
    return results, changes
