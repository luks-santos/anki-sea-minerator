from __future__ import annotations


class DuplicateNoteError(Exception):
    pass


class CollectionAnkiClient:
    def __init__(self, col) -> None:
        self._col = col

    def deck_names(self) -> list[str]:
        return [d.name for d in self._col.decks.all_names_and_ids()]

    def tag_names(self) -> list[str]:
        return list(self._col.tags.all())

    def add_note(
        self,
        deck: str,
        model: str,
        fields: dict[str, str],
        tags: list[str] | None = None,
    ) -> int:
        notetype = self._col.models.by_name(model)
        if notetype is None:
            raise ValueError(f"note type '{model}' not found in the collection")

        note = self._col.new_note(notetype)
        for name, value in fields.items():
            note[name] = value
        note.tags = list(tags or [])

        # `duplicate_or_empty()` returns truthy for either a duplicate *or* an
        # empty first field, so this exception fires for both cases even
        # though its name only names one of them.
        if note.duplicate_or_empty():
            raise DuplicateNoteError(
                "a note with this front already exists, or the front is empty"
            )

        # `col.decks.id(deck)` looks up the deck by name but also *creates*
        # it if no deck with that name exists yet -- this is not a pure read.
        deck_id = self._col.decks.id(deck)
        self._col.add_note(note, deck_id)
        return note.id
