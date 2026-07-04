import pytest

from minerator.tts.base import get_engine
from minerator.tts.edge import EdgeTTS
from minerator.tts.gtts_engine import GttsTTS


def test_factory_returns_edge():
    engine = get_engine("edge", "en-US-AriaNeural")
    assert isinstance(engine, EdgeTTS)


def test_factory_returns_gtts():
    assert isinstance(get_engine("gtts", "en-US-EmmaNeural"), GttsTTS)


def test_factory_derives_gtts_lang_from_voice_prefix():
    engine = get_engine("gtts", "pt-BR-FranciscaNeural")
    assert engine._lang == "pt"


def test_factory_gtts_defaults_to_english_when_voice_is_empty():
    engine = get_engine("gtts", "")
    assert engine._lang == "en"


def test_factory_rejects_unknown():
    with pytest.raises(ValueError):
        get_engine("nope", "x")


def test_gtts_synthesize_returns_bytes(monkeypatch):
    class FakeGTTS:
        def __init__(self, text, lang="en"):
            self.text = text

        def write_to_fp(self, fp):
            fp.write(b"ID3-fake-mp3")

    monkeypatch.setattr("minerator.tts.gtts_engine.gTTS", FakeGTTS)
    data = GttsTTS().synthesize("hello")
    assert data == b"ID3-fake-mp3"


def test_edge_synthesize_concatenates_audio_chunks(monkeypatch):
    class FakeCommunicate:
        def __init__(self, text, voice):
            self.text, self.voice = text, voice

        async def stream(self):
            yield {"type": "audio", "data": b"aa"}
            yield {"type": "WordBoundary"}
            yield {"type": "audio", "data": b"bb"}

    monkeypatch.setattr("minerator.tts.edge.edge_tts.Communicate", FakeCommunicate)
    data = EdgeTTS("en-US-AriaNeural").synthesize("hi")
    assert data == b"aabb"
