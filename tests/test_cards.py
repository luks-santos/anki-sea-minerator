from minerator.cards import build_back, highlight_html
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
