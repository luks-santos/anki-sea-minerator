import base64

from minerator.config import Config
from minerator.flow import create_card
from minerator.models import Sentence, WordBlock


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


def make_word():
    return WordBlock(
        expression="give up", explanation="", translations=["Desistir"],
        grammar_class="Phrasal Verb", sentences=[],
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
