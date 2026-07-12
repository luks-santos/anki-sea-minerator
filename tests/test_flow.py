import base64

from minerator.config import Config
from minerator.flow import create_card, create_imported_card, create_imported_cards
from minerator.models import ImportedCard, Sentence, WordBlock


class FakeAnki:
    def __init__(self):
        self.media = []
        self.notes = []

    def store_media_file(self, filename, data_b64):
        self.media.append((filename, data_b64))
        return filename

    def add_note(self, deck, model, fields, tags=None):
        self.notes.append({"deck": deck, "model": model, "fields": fields})
        return 999


class FakeTTS:
    def synthesize(self, text):
        return b"AUDIO"


class FailingTTS:
    def synthesize(self, text):
        raise RuntimeError("tts down")


class FailingAddNoteAnki(FakeAnki):
    def add_note(self, deck, model, fields, tags=None):
        raise RuntimeError("AnkiConnect: deck not found")


def make_word():
    return WordBlock(
        expression="give up",
        explanation="",
        translations=["Desistir"],
        grammar_class="Phrasal Verb",
        sentences=[],
    )


def test_create_card_stores_audio_and_adds_note():
    anki = FakeAnki()
    cfg = Config()
    sentence = Sentence(text="Never give up.", highlight="give up")
    result = create_card(make_word(), sentence, cfg, "English", anki, FakeTTS())

    assert result.created is True
    assert result.note_id == 999
    assert result.warning is None
    # media stored with base64 of audio bytes
    filename, data_b64 = anki.media[0]
    assert base64.b64decode(data_b64) == b"AUDIO"
    # front references the sound and highlight; back formatted
    note = anki.notes[0]
    assert f"[sound:{filename}]" in note["fields"]["Frente"]
    assert '<span style="color:#2563eb">give up</span>' in note["fields"]["Frente"]
    assert note["fields"]["Verso"] == "Give up: Desistir (Phrasal Verb)"


def test_create_card_survives_tts_failure_with_warning():
    anki = FakeAnki()
    sentence = Sentence(text="Never give up.", highlight="give up")
    result = create_card(make_word(), sentence, Config(), "English", anki, FailingTTS())

    assert result.created is True
    assert result.warning is not None
    assert anki.media == []  # no media stored
    assert "[sound:" not in anki.notes[0]["fields"]["Frente"]


def test_create_card_warns_when_highlight_missing():
    anki = FakeAnki()
    sentence = Sentence(text="Totally unrelated.", highlight="give up")
    result = create_card(make_word(), sentence, Config(), "English", anki, FakeTTS())

    assert result.created is True
    assert result.warning is not None
    assert "<span" not in anki.notes[0]["fields"]["Frente"]


def test_create_card_survives_add_note_failure_with_warning():
    anki = FailingAddNoteAnki()
    sentence = Sentence(text="Never give up.", highlight="give up")
    result = create_card(make_word(), sentence, Config(), "English", anki, FakeTTS())

    assert result.created is False
    assert result.note_id is None
    assert result.warning is not None
    assert "deck not found" in result.warning


def test_create_imported_card_strips_tag_for_tts_but_keeps_it_on_front():
    anki = FakeAnki()
    cfg = Config()
    card = ImportedCard(
        front="[Grammar] We had a bad day.", back="Nós tivemos um dia ruim."
    )

    captured = {}

    class CapturingTTS:
        def synthesize(self, text):
            captured["text"] = text
            return b"AUDIO"

    result = create_imported_card(card, cfg, "English", anki, CapturingTTS())

    assert result.created is True
    assert captured["text"] == "We had a bad day."
    note = anki.notes[0]
    assert note["fields"]["Frente"] == (
        f"[Grammar] We had a bad day. [sound:{anki.media[0][0]}]"
    )
    assert note["fields"]["Verso"] == "Nós tivemos um dia ruim."


def test_create_imported_card_keeps_tag_in_tts_when_stripping_disabled():
    anki = FakeAnki()
    cfg = Config(strip_bracket_tags=False)
    card = ImportedCard(front="[Grammar] We had a bad day.", back="Verso.")

    captured = {}

    class CapturingTTS:
        def synthesize(self, text):
            captured["text"] = text
            return b"AUDIO"

    create_imported_card(card, cfg, "English", anki, CapturingTTS())
    assert captured["text"] == "[Grammar] We had a bad day."


def test_create_imported_card_without_tag_is_unaffected():
    anki = FakeAnki()
    cfg = Config()
    card = ImportedCard(front="Plain sentence.", back="Frase simples.")

    captured = {}

    class CapturingTTS:
        def synthesize(self, text):
            captured["text"] = text
            return b"AUDIO"

    create_imported_card(card, cfg, "English", anki, CapturingTTS())
    assert captured["text"] == "Plain sentence."


def test_create_imported_card_survives_tts_failure_with_warning():
    anki = FakeAnki()
    card = ImportedCard(front="[Grammar] We had a bad day.", back="Verso.")
    result = create_imported_card(card, Config(), "English", anki, FailingTTS())

    assert result.created is True
    assert result.warning is not None
    assert anki.media == []
    assert "[sound:" not in anki.notes[0]["fields"]["Frente"]
    assert anki.notes[0]["fields"]["Frente"] == "[Grammar] We had a bad day."


def test_create_imported_card_survives_add_note_failure_with_warning():
    anki = FailingAddNoteAnki()
    card = ImportedCard(front="[Grammar] We had a bad day.", back="Verso.")
    result = create_imported_card(card, Config(), "English", anki, FakeTTS())

    assert result.created is False
    assert result.note_id is None
    assert result.warning is not None
    assert "deck not found" in result.warning


def test_create_imported_cards_maps_over_list():
    anki = FakeAnki()
    cards = [
        ImportedCard(front="Front one.", back="Back one."),
        ImportedCard(front="Front two.", back="Back two."),
    ]
    results = create_imported_cards(cards, Config(), "English", anki, FakeTTS())
    assert len(results) == 2
    assert all(r.created for r in results)
