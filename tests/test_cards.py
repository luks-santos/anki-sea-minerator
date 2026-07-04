from minerator.cards import audio_filename, build_back, build_front, highlight_html
from minerator.models import WordBlock


def test_highlight_wraps_first_case_insensitive_occurrence():
    out = highlight_html("The Give up moment", "give up", "#2563eb")
    assert out == 'The <span style="color:#2563eb">Give up</span> moment'


def test_highlight_returns_text_when_not_found():
    assert highlight_html("Hello world", "xyz", "#2563eb") == "Hello world"


def test_highlight_empty_highlight_is_noop():
    assert highlight_html("Hello world", "", "#2563eb") == "Hello world"


def test_audio_filename_is_stable_and_prefixed():
    a = audio_filename("Never give up.")
    b = audio_filename("Never give up.")
    assert a == b
    assert a.startswith("minerator-") and a.endswith(".mp3")


def test_build_front_with_audio():
    out = build_front("Never give up.", "give up", "#2563eb", "minerator-abc.mp3")
    assert out == 'Never <span style="color:#2563eb">give up</span>. [sound:minerator-abc.mp3]'


def test_build_front_without_audio():
    out = build_front("Never give up.", "give up", "#2563eb", None)
    assert out == 'Never <span style="color:#2563eb">give up</span>.'


def test_build_back_formats_expression_translations_class():
    word = WordBlock(
        expression="give up",
        explanation="",
        translations=["Desistir", "Parar"],
        grammar_class="Phrasal Verb",
        sentences=[],
    )
    assert build_back(word) == "Give up: Desistir, Parar (Phrasal Verb)"
