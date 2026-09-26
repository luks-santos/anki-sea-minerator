from seaminerator.core.config import Config
from seaminerator.core.flow import (
    create_card,
    create_cards_for_selection,
    create_imported_card,
    create_imported_cards,
)
from seaminerator.core.models import ImportedCard, Sentence, WordBlock


class FakeAnki:
    def __init__(self):
        self.notes = []

    def add_note(self, deck, model, fields, tags=None):
        self.notes.append(
            {"deck": deck, "model": model, "fields": fields, "tags": tags}
        )
        return 999


class FailingAddNoteAnki(FakeAnki):
    def add_note(self, deck, model, fields, tags=None):
        raise RuntimeError("deck not found")


def make_word():
    return WordBlock(
        expression="give up",
        explanation="",
        translations=["Desistir"],
        class_tag="phrasal-verb",
        sentences=[],
    )


def test_create_card_adds_note_with_highlight_and_no_audio():
    anki = FakeAnki()
    sentence = Sentence(text="Never give up.", highlight="give up")

    result = create_card(make_word(), sentence, Config(), "English", anki)

    assert result.created is True
    assert result.note_id == 999
    assert result.warning is None
    note = anki.notes[0]
    assert note["deck"] == "English"
    assert note["tags"] == ["anki-sea-minerator"]
    assert '<span style="color:#2563eb">give up</span>' in note["fields"]["Front"]
    assert "[sound:" not in note["fields"]["Front"]
    assert note["fields"]["Back"] == "Give up: Desistir (Phrasal verb)"


def test_create_card_warns_when_highlight_missing():
    anki = FakeAnki()
    sentence = Sentence(text="Totally unrelated.", highlight="give up")

    result = create_card(make_word(), sentence, Config(), "English", anki)

    assert result.created is True
    assert result.warning is not None
    assert "<span" not in anki.notes[0]["fields"]["Front"]


def test_create_card_survives_add_note_failure_with_warning():
    anki = FailingAddNoteAnki()
    sentence = Sentence(text="Never give up.", highlight="give up")

    result = create_card(make_word(), sentence, Config(), "English", anki)

    assert result.created is False
    assert result.note_id is None
    assert "deck not found" in result.warning


def test_create_cards_for_selection_maps_over_sentences():
    anki = FakeAnki()
    selected = [
        Sentence(text="Never give up.", highlight="give up"),
        Sentence(text="He gave up smoking.", highlight="gave up"),
    ]

    results = create_cards_for_selection(
        make_word(), selected, Config(), "English", anki
    )

    assert len(results) == 2
    assert all(r.created for r in results)


def test_create_imported_card_keeps_bracket_tag_on_front():
    anki = FakeAnki()
    card = ImportedCard(
        front="[Grammar] We had a bad day.", back="Nós tivemos um dia ruim."
    )

    result = create_imported_card(card, Config(), "English", anki)

    assert result.created is True
    note = anki.notes[0]
    assert note["fields"]["Front"] == "[Grammar] We had a bad day."
    assert note["fields"]["Back"] == "Nós tivemos um dia ruim."


def test_create_imported_cards_maps_over_list():
    anki = FakeAnki()
    cards = [
        ImportedCard(front="Front one.", back="Back one."),
        ImportedCard(front="Front two.", back="Back two."),
    ]

    results = create_imported_cards(cards, Config(), "English", anki)

    assert len(results) == 2
    assert all(r.created for r in results)
