from seaminerator.core.audio.base import AudioError, media_name, speech_text


def test_speech_text_keeps_a_plain_sentence():
    assert speech_text("She has given up smoking.") == "She has given up smoking."


def test_speech_text_drops_tags_and_unescapes_entities():
    raw = 'I&#39;ve <span style="color:#2563eb">got</span>  it&nbsp;now'
    assert speech_text(raw) == "I've got it now"


def test_speech_text_strips_a_leading_label_only_when_asked():
    assert speech_text("[Grammar] We had a bad day.", strip_label=True) == (
        "We had a bad day."
    )
    assert speech_text("[Grammar] We had a bad day.") == "[Grammar] We had a bad day."
    assert speech_text("[Grammar] I&#39;ve <b>got</b> it", strip_label=True) == (
        "I've got it"
    )


def test_media_name_is_stable_and_depends_on_every_input():
    name = media_name("google", "us", "Hi.")

    assert name == media_name("google", "us", "Hi.")
    assert name.startswith("sea-minerator-") and name.endswith(".mp3")
    assert len(name) == len("sea-minerator-") + 20 + len(".mp3")
    others = {
        media_name("gemini", "us", "Hi."),
        media_name("google", "co.uk", "Hi."),
        media_name("google", "us", "Hi!"),
    }
    assert name not in others and len(others) == 3


def test_audio_error_says_whether_the_source_is_down():
    assert AudioError("x", source_down=True).source_down is True
    assert AudioError("x", source_down=False).source_down is False
    assert str(AudioError("boom", source_down=False)) == "boom"
