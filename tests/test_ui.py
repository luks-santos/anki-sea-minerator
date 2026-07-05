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
