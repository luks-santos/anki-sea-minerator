import pytest

from seaminerator.anki.collection_client import (
    CollectionAnkiClient,
    DuplicateNoteError,
)
from seaminerator.anki.notetype import NOTE_TYPE_NAME, ensure_notetype
from seaminerator.core.config import Config
from seaminerator.core.flow import create_card
from seaminerator.core.models import Sentence, WordBlock


@pytest.fixture
def client(col):
    ensure_notetype(col, "en_US")
    return CollectionAnkiClient(col)


def test_deck_names_includes_the_default_deck(client):
    assert "Default" in client.deck_names()


def test_add_note_creates_a_real_note_and_returns_its_id(client, col):
    note_id = client.add_note(
        deck="English",
        model=NOTE_TYPE_NAME,
        fields={"Front": "Never give up.", "Back": "Give up: Desistir"},
        tags=["anki-sea-minerator"],
    )

    assert note_id > 0
    note = col.get_note(note_id)
    assert note["Front"] == "Never give up."
    assert note["Back"] == "Give up: Desistir"
    assert note.tags == ["anki-sea-minerator"]


def test_add_note_creates_the_deck_when_missing(client, col):
    assert "English" not in client.deck_names()

    client.add_note(
        deck="English", model=NOTE_TYPE_NAME, fields={"Front": "a", "Back": "b"}
    )

    assert "English" in client.deck_names()


def test_add_note_puts_the_card_in_the_requested_deck(client, col):
    note_id = client.add_note(
        deck="English", model=NOTE_TYPE_NAME, fields={"Front": "a", "Back": "b"}
    )

    card = col.get_note(note_id).cards()[0]
    assert col.decks.name(card.did) == "English"


def test_add_note_rejects_a_duplicate_front(client):
    fields = {"Front": "Never give up.", "Back": "x"}
    client.add_note(deck="English", model=NOTE_TYPE_NAME, fields=fields)

    with pytest.raises(DuplicateNoteError):
        client.add_note(deck="English", model=NOTE_TYPE_NAME, fields=fields)


def test_add_note_rejects_an_empty_front(client):
    with pytest.raises(DuplicateNoteError):
        client.add_note(
            deck="English", model=NOTE_TYPE_NAME, fields={"Front": "", "Back": "b"}
        )


def test_add_note_raises_for_an_unknown_note_type(client):
    with pytest.raises(ValueError, match="note type"):
        client.add_note(deck="English", model="Nope", fields={"Front": "a"})


def test_create_card_end_to_end_against_a_real_collection(client, col):
    word = WordBlock(
        expression="give up",
        explanation="",
        translations=["Desistir"],
        class_tag="phrasal-verb",
        sentences=[],
    )
    sentence = Sentence(text="Never give up.", highlight="give up")

    result = create_card(word, sentence, Config(), "English", client)

    assert result.created is True
    note = col.get_note(result.note_id)
    assert '<span style="color:#2563eb">give up</span>' in note["Front"]
    assert note["Back"] == "Give up: Desistir (Phrasal verb)"
