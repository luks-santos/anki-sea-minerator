import os

import pytest

from minerator.tts import player


def test_play_audio_writes_temp_file_plays_and_removes_it(monkeypatch):
    captured = {}

    def fake_playsound(path):
        captured["path"] = path
        with open(path, "rb") as fh:
            captured["contents"] = fh.read()
        captured["existed_during_playback"] = os.path.exists(path)

    monkeypatch.setattr(player.playsound3, "playsound", fake_playsound)

    player.play_audio(b"fake-mp3-bytes")

    assert captured["contents"] == b"fake-mp3-bytes"
    assert captured["existed_during_playback"] is True
    assert not os.path.exists(captured["path"])


def test_play_audio_removes_temp_file_even_if_playback_fails(monkeypatch):
    captured = {}

    def fake_playsound(path):
        captured["path"] = path
        raise RuntimeError("playback device busy")

    monkeypatch.setattr(player.playsound3, "playsound", fake_playsound)

    with pytest.raises(RuntimeError):
        player.play_audio(b"fake-mp3-bytes")

    assert not os.path.exists(captured["path"])
