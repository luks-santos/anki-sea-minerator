from minerator.cards import (
    audio_filename,
    build_back,
    build_front,
    highlight_html,
    strip_bracket_tag,
)
from minerator.models import WordBlock


def test_highlight_wraps_first_case_insensitive_occurrence():
    out = highlight_html("The Give up moment", "give up", "#2563eb")
    assert out == 'The <span style="color:#2563eb">Give up</span> moment'


def test_highlight_returns_text_when_not_found():
    assert highlight_html("Hello world", "xyz", "#2563eb") == "Hello world"


def test_highlight_empty_highlight_is_noop():
    assert highlight_html("Hello world", "", "#2563eb") == "Hello world"


def test_highlight_survives_unicode_casefold_expansion():
    # 'İ'.lower() expands to two code points ("i" + combining dot above),
    # which used to desync a lower()-based index from the original string.
    out = highlight_html("I visited İstanbul last year", "istanbul", "#2563eb")
    assert out == 'I visited <span style="color:#2563eb">İstanbul</span> last year'


def test_audio_filename_is_stable_and_prefixed():
    a = audio_filename("Never give up.")
    b = audio_filename("Never give up.")
    assert a == b
    assert a.startswith("minerator-") and a.endswith(".mp3")


def test_build_front_with_audio():
    highlighted = 'Never <span style="color:#2563eb">give up</span>.'
    out = build_front(highlighted, "minerator-abc.mp3")
    assert (
        out
        == 'Never <span style="color:#2563eb">give up</span>. [sound:minerator-abc.mp3]'
    )


def test_build_front_without_audio():
    highlighted = 'Never <span style="color:#2563eb">give up</span>.'
    assert build_front(highlighted, None) == highlighted


def test_build_back_formats_expression_translations_class():
    word = WordBlock(
        expression="give up",
        explanation="",
        translations=["Desistir", "Parar"],
        grammar_class="Phrasal Verb",
        sentences=[],
    )
    assert build_back(word) == "Give up: Desistir, Parar (Phrasal Verb)"


def test_build_back_preserves_internal_capitals():
    word = WordBlock(
        expression="NASA",
        explanation="",
        translations=["NASA"],
        grammar_class="Noun",
        sentences=[],
    )
    assert build_back(word) == "NASA: NASA (Noun)"


def test_strip_bracket_tag_removes_leading_tag():
    assert strip_bracket_tag("[Grammar] We had a bad day.") == "We had a bad day."


def test_strip_bracket_tag_noop_without_tag():
    assert strip_bracket_tag("We had a bad day.") == "We had a bad day."


def test_strip_bracket_tag_handles_empty_brackets():
    assert strip_bracket_tag("[] Empty tag.") == "Empty tag."


def test_strip_bracket_tag_handles_special_characters_in_tag():
    assert strip_bracket_tag("[a.b*c+d] Weird chars.") == "Weird chars."


def test_strip_bracket_tag_ignores_mid_string_brackets():
    assert strip_bracket_tag("Mid [Grammar] sentence.") == "Mid [Grammar] sentence."
