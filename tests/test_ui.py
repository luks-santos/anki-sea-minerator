from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
import pytest

from minerator.models import Sentence, WordBlock
from minerator import ui


def _block():
    return WordBlock(
        expression="give up",
        explanation="Desistir de algo; parar de tentar.",
        translations=["desistir", "abandonar"],
        grammar_class="Phrasal Verb",
        sentences=[Sentence("Never give up.", "give up", "imperative")],
    )


def test_render_block_shows_expression_grammar_and_translations():
    with ui.console.capture() as cap:
        ui.render_block(_block())
    out = cap.get()
    assert "give up" in out
    assert "Phrasal Verb" in out
    assert "Desistir de algo" in out
    assert "desistir" in out


def test_render_block_escapes_bracket_like_content_in_explanation():
    block = WordBlock(
        expression="bird",
        explanation="a bird [BrE] term for flying animal",
        translations=["pássaro [informal]"],
        grammar_class="Noun [archaic]",
        sentences=[Sentence("The bird flew.", "bird", "noun")],
    )
    with ui.console.capture() as cap:
        ui.render_block(block)
    out = cap.get()
    assert "[BrE]" in out
    assert "[informal]" in out
    assert "[archaic]" in out


def test_lines_to_words_strips_and_drops_blanks():
    assert ui._lines_to_words("  give up \n\n break down \n") == ["give up", "break down"]


def test_read_words_alt_enter_makes_newline_and_enter_submits():
    with create_pipe_input() as inp:
        inp.send_text("give up\x1b\rbreak down\r")  # Alt+Enter, then Enter
        with create_app_session(input=inp, output=DummyOutput()):
            assert ui.read_words() == ["give up", "break down"]


def test_read_words_ctrl_c_returns_empty():
    with create_pipe_input() as inp:
        inp.send_text("\x03")  # Ctrl+C
        with create_app_session(input=inp, output=DummyOutput()):
            assert ui.read_words() == []


def test_mining_status_prints_summary_on_success():
    with ui.console.capture() as cap:
        with ui.mining_status(3):
            pass
    assert "3 words mined" in cap.get()


def test_mining_status_reraises_and_skips_summary_on_error():
    with ui.console.capture() as cap:
        with pytest.raises(ValueError):
            with ui.mining_status(3):
                raise ValueError("boom")
    assert "mined" not in cap.get()


def test_creating_cards_status_runs_body():
    executed = {"ran": False}
    with ui.creating_cards_status(2):
        executed["ran"] = True
    assert executed["ran"] is True


def test_creating_cards_status_reraises_errors():
    with pytest.raises(ValueError):
        with ui.creating_cards_status(2):
            raise ValueError("boom")


def test_resolve_selection_checked_wins():
    s1, s2 = Sentence("a", "a"), Sentence("b", "b")
    assert ui._resolve_selection([s1, s2], s1) == [s1, s2]


def test_resolve_selection_empty_uses_pointed_sentence():
    s1 = Sentence("a", "a")
    assert ui._resolve_selection([], s1) == [s1]


def test_resolve_selection_skip_row_returns_empty():
    assert ui._resolve_selection([], ui._SKIP) == []


def test_resolve_selection_checked_skip_returns_empty():
    s1 = Sentence("a", "a")
    assert ui._resolve_selection([ui._SKIP, s1], s1) == []


def test_select_sentences_immediate_enter_skips():
    block = WordBlock("give up", "", [], "", [Sentence("Never give up.", "give up")])
    with create_pipe_input() as inp:
        inp.send_text("\r")  # Enter with pointer on the skip row
        with create_app_session(input=inp, output=DummyOutput()):
            assert ui.select_sentences(block) == []


def test_select_sentences_down_then_enter_picks_pointed():
    s = Sentence("Never give up.", "give up")
    block = WordBlock("give up", "", [], "", [s])
    with create_pipe_input() as inp:
        inp.send_text("\x1b[B\r")  # Down onto the sentence, then Enter
        with create_app_session(input=inp, output=DummyOutput()):
            assert ui.select_sentences(block) == [s]


def test_select_sentences_space_toggles_then_enter():
    s = Sentence("Never give up.", "give up")
    block = WordBlock("give up", "", [], "", [s])
    with create_pipe_input() as inp:
        inp.send_text("\x1b[B \r")  # Down, space (toggle), Enter
        with create_app_session(input=inp, output=DummyOutput()):
            assert ui.select_sentences(block) == [s]
