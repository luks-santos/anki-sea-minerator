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
