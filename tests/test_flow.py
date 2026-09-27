from seaminerator.core.config import Config
from seaminerator.core.flow import (
    create_card,
    create_cards_for_selection,
    create_imported_card,
    create_imported_cards,
    imported_back,
    imported_front,
    prepare_import,
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


def test_create_card_puts_the_sentence_topics_on_the_back_not_in_tags():
    anki = FakeAnki()
    sentence = Sentence(
        text="He has given up.", highlight="given up", topics=["present-perfect"]
    )

    create_card(make_word(), sentence, Config(), "English", anki)

    note = anki.notes[0]
    assert note["tags"] == ["anki-sea-minerator"]
    assert note["fields"]["Back"] == (
        "Give up: Desistir (Phrasal verb · present-perfect)"
    )


def test_create_cards_for_selection_gives_each_card_its_own_topics():
    anki = FakeAnki()
    selected = [
        Sentence(text="He gave up.", highlight="gave up", topics=["past-simple"]),
        Sentence(text="Never give up.", highlight="give up"),
    ]

    create_cards_for_selection(make_word(), selected, Config(), "English", anki)

    backs = [note["fields"]["Back"] for note in anki.notes]
    assert backs == [
        "Give up: Desistir (Phrasal verb · past-simple)",
        "Give up: Desistir (Phrasal verb)",
    ]


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


def test_create_imported_card_turns_the_prefix_into_a_label_and_adds_the_topic():
    anki = FakeAnki()
    card = ImportedCard(
        front="[Grammar] We had a bad day.", back="Nós tivemos um dia ruim."
    )

    result = create_imported_card(card, Config(), "English", anki, topic="Past Simple")

    assert result.created is True
    note = anki.notes[0]
    assert note["fields"]["Front"] == (
        '<span class="sm-label" data-label="Grammar"></span>We had a bad day.'
    )
    assert note["fields"]["Back"] == "Nós tivemos um dia ruim. (past-simple)"
    assert note["tags"] == ["anki-sea-minerator"]


def test_create_imported_card_without_topic_keeps_the_back():
    anki = FakeAnki()
    card = ImportedCard(front="Plain.", back="Simples.")

    create_imported_card(card, Config(), "English", anki)

    assert anki.notes[0]["fields"] == {"Front": "Plain.", "Back": "Simples."}


def test_imported_front_converts_only_a_leading_bracket_prefix():
    assert imported_front("[Grammar] I've just arrived.") == (
        '<span class="sm-label" data-label="Grammar"></span>I\'ve just arrived.'
    )
    assert imported_front("He said [sic] hi.") == "He said [sic] hi."
    assert imported_front("No prefix.") == "No prefix."


def test_imported_front_escapes_the_label():
    assert imported_front('[A&"B] x') == (
        '<span class="sm-label" data-label="A&amp;&quot;B"></span>x'
    )


def test_imported_back_appends_the_normalized_topic():
    assert imported_back("Eu acabei de chegar.", "present perfect") == (
        "Eu acabei de chegar. (present-perfect)"
    )
    assert imported_back("Eu acabei de chegar.", "  ") == "Eu acabei de chegar."
    assert imported_back("Eu acabei de chegar.", "") == "Eu acabei de chegar."


def test_create_imported_cards_maps_over_list():
    anki = FakeAnki()
    cards = [
        ImportedCard(front="Front one.", back="Back one."),
        ImportedCard(front="Front two.", back="Back two."),
    ]

    results = create_imported_cards(cards, Config(), "English", anki)

    assert len(results) == 2
    assert all(r.created for r in results)


def test_imported_back_does_not_repeat_a_topic_already_there():
    back = "Eu acabei de chegar. (present-perfect)"
    assert imported_back(back, "present perfect") == back


LABEL_ONLY = """[Grammar]
Eu acabei de chegar.

[Grammar] Have you seen him?
Você viu ele?"""


def test_prepare_import_skips_a_front_that_has_only_a_label():
    plan = prepare_import(LABEL_ONLY, "present perfect")

    assert [c.front for c in plan.cards] == ["[Grammar] Have you seen him?"]
    assert plan.warnings == ["card '[Grammar]' skipped: the front has only a label"]
    assert plan.topic == "present-perfect"


def test_prepare_import_keeps_the_parse_warnings():
    plan = prepare_import("front only", "")
    assert plan.cards == []
    assert plan.warnings == ["block 1 skipped: expected 2 lines (front, back), got 1"]


def test_prepare_import_warns_about_a_topic_that_normalizes_to_nothing():
    plan = prepare_import("F.\nB.", " ??? ")
    assert plan.topic == ""
    assert plan.warnings == ["topic '???' ignored: use letters, digits and spaces"]


def test_prepare_import_refuses_a_reserved_tag_as_topic():
    plan = prepare_import("F.\nB.", "anki-sea-minerator")
    assert plan.topic == ""
    assert plan.warnings == ["topic 'anki-sea-minerator' ignored: it is a reserved tag"]


def test_prepare_import_accepts_a_class_name_as_topic():
    plan = prepare_import("F.\nB.", "phrasal verb")
    assert plan.topic == "phrasal-verb"
    assert plan.warnings == []
