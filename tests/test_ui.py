import re

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from rich.console import Console

from minerator import ui
from minerator.models import ImportedCard, Sentence, WordBlock

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


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


def test_render_block_indents_wrapped_explanation_lines(monkeypatch):
    narrow = Console(theme=ui.THEME, width=60)
    monkeypatch.setattr(ui, "console", narrow)
    block = WordBlock(
        expression="mundo",
        explanation=(
            "Substantivo. Refere-se ao planeta Terra e a tudo que existe "
            "nele, incluindo a humanidade e a sociedade."
        ),
        translations=["Mundo", "Planeta", "Terra"],
        grammar_class="Substantivo",
        sentences=[],
    )
    with narrow.capture() as cap:
        ui.render_block(block)
    lines = [_strip_ansi(line) for line in cap.get().splitlines() if line.strip()]
    meaning_idx = next(i for i, line in enumerate(lines) if "Meaning" in line)
    continuation = lines[meaning_idx + 1]
    assert not continuation.startswith("Substantivo")
    leading_spaces = len(continuation) - len(continuation.lstrip(" "))
    assert leading_spaces >= 8


def test_lines_to_words_strips_and_drops_blanks():
    assert ui._lines_to_words("  give up \n\n break down \n") == [
        "give up",
        "break down",
    ]


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


def test_read_import_pairs_alt_enter_makes_newline_and_enter_submits():
    with create_pipe_input() as inp:
        inp.send_text(
            "[Grammar] We had a bad day.\x1b\rNós tivemos um dia ruim.\r"
        )  # Alt+Enter, then Enter
        with create_app_session(input=inp, output=DummyOutput()):
            assert (
                ui.read_import_pairs()
                == "[Grammar] We had a bad day.\nNós tivemos um dia ruim."
            )


def test_read_import_pairs_ctrl_c_returns_empty_string():
    with create_pipe_input() as inp:
        inp.send_text("\x03")  # Ctrl+C
        with create_app_session(input=inp, output=DummyOutput()):
            assert ui.read_import_pairs() == ""


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


def test_select_sentences_immediate_enter_picks_first_sentence():
    s = Sentence("Never give up.", "give up")
    block = WordBlock("give up", "", [], "", [s])
    with create_pipe_input() as inp:
        inp.send_text("\r")  # Enter with pointer defaulting to the first sentence
        with create_app_session(input=inp, output=DummyOutput()):
            assert ui.select_sentences(block) == [s]


def test_select_sentences_navigate_to_skip_row_returns_empty():
    s = Sentence("Never give up.", "give up")
    block = WordBlock("give up", "", [], "", [s])
    with create_pipe_input() as inp:
        inp.send_text("\x1b[B\r")  # Down onto the trailing skip row, then Enter
        with create_app_session(input=inp, output=DummyOutput()):
            assert ui.select_sentences(block) == []


def test_select_sentences_space_toggles_then_enter():
    s = Sentence("Never give up.", "give up")
    block = WordBlock("give up", "", [], "", [s])
    with create_pipe_input() as inp:
        inp.send_text(" \r")  # Space toggles the pointed sentence, then Enter
        with create_app_session(input=inp, output=DummyOutput()):
            assert ui.select_sentences(block) == [s]


def test_select_sentences_down_then_enter_picks_second_sentence():
    s1 = Sentence("Never give up.", "give up")
    s2 = Sentence("Don't give up now.", "give up")
    block = WordBlock("give up", "", [], "", [s1, s2])
    with create_pipe_input() as inp:
        inp.send_text("\x1b[B\r")  # Down onto the second sentence, then Enter
        with create_app_session(input=inp, output=DummyOutput()):
            assert ui.select_sentences(block) == [s2]


def test_select_sentences_ctrl_c_raises_keyboard_interrupt():
    s = Sentence("Never give up.", "give up")
    block = WordBlock("give up", "", [], "", [s])
    with create_pipe_input() as inp:
        inp.send_text("\x03")  # Ctrl+C
        with create_app_session(input=inp, output=DummyOutput()):
            with pytest.raises(KeyboardInterrupt):
                ui.select_sentences(block)


def test_fetch_and_play_synthesizes_caches_and_plays(monkeypatch):
    calls = {"synthesize": 0, "play": []}

    class FakeTTS:
        def synthesize(self, text):
            calls["synthesize"] += 1
            return f"audio-for-{text}".encode()

    monkeypatch.setattr(ui, "play_audio", lambda data: calls["play"].append(data))

    class FakeApp:
        def __init__(self):
            self.invalidated = 0

        def invalidate(self):
            self.invalidated += 1

    cache: dict = {}
    state = ui._PreviewState()
    app = FakeApp()

    ui._fetch_and_play(FakeTTS(), cache, "Never give up.", state, app)

    assert calls["synthesize"] == 1
    assert calls["play"] == [b"audio-for-Never give up."]
    assert cache["Never give up."] == b"audio-for-Never give up."
    assert state.text == ""
    assert state.busy is False
    assert app.invalidated == 1


def test_fetch_and_play_uses_cache_on_second_call(monkeypatch):
    calls = {"synthesize": 0}

    class FakeTTS:
        def synthesize(self, text):
            calls["synthesize"] += 1
            return b"cached-audio"

    monkeypatch.setattr(ui, "play_audio", lambda data: None)

    class FakeApp:
        def invalidate(self):
            pass

    cache = {"Never give up.": b"cached-audio"}
    state = ui._PreviewState()

    ui._fetch_and_play(FakeTTS(), cache, "Never give up.", state, FakeApp())

    assert calls["synthesize"] == 0


def test_fetch_and_play_sets_warning_status_on_failure():
    class FakeTTS:
        def synthesize(self, text):
            raise RuntimeError("network down")

    class FakeApp:
        def invalidate(self):
            pass

    cache: dict = {}
    state = ui._PreviewState()

    ui._fetch_and_play(FakeTTS(), cache, "Never give up.", state, FakeApp())

    assert "failed" in state.text.lower()
    assert state.busy is False


def test_select_sentences_p_previews_pointed_sentence_then_enter_confirms(monkeypatch):
    def sync_start(tts, cache, text, state, app):
        ui._fetch_and_play(tts, cache, text, state, app)

    monkeypatch.setattr(ui, "_start_preview_thread", sync_start)

    played = []
    monkeypatch.setattr(ui, "play_audio", lambda data: played.append(data))

    class FakeTTS:
        def synthesize(self, text):
            return f"audio:{text}".encode()

    s = Sentence("Never give up.", "give up")
    block = WordBlock("give up", "", [], "", [s])

    with create_pipe_input() as inp:
        inp.send_text("p\r")  # p previews the pointed sentence, then Enter confirms
        with create_app_session(input=inp, output=DummyOutput()):
            result = ui.select_sentences(block, FakeTTS())

    assert result == [s]
    assert played == [b"audio:Never give up."]


def test_select_sentences_p_does_nothing_without_tts():
    s = Sentence("Never give up.", "give up")
    block = WordBlock("give up", "", [], "", [s])
    with create_pipe_input() as inp:
        inp.send_text(
            "p\r"
        )  # p is a no-op with no tts configured; Enter still confirms
        with create_app_session(input=inp, output=DummyOutput()):
            assert ui.select_sentences(block) == [s]


def test_render_block_omits_spacer_row_without_explanation_or_translations():
    block = WordBlock(
        expression="give up",
        explanation="",
        translations=[],
        grammar_class="Phrasal Verb",
        sentences=[],
    )
    with ui.console.capture() as cap:
        ui.render_block(block)
    stripped_lines = [_strip_ansi(line) for line in cap.get().splitlines()]
    non_blank = [line for line in stripped_lines if line.strip()]
    assert len(non_blank) == 3  # rule + heading line + Card back line, no spacer row
    assert "Card back" in non_blank[2]


def test_render_import_preview_lists_front_and_back():
    cards = [
        ImportedCard(
            front="[Grammar] We had a bad day.", back="Nós tivemos um dia ruim."
        ),
        ImportedCard(front="Plain sentence.", back="Frase simples."),
    ]
    with ui.console.capture() as cap:
        ui.render_import_preview(cards)
    out = _strip_ansi(cap.get())
    assert "We had a bad day." in out
    assert "Nós tivemos um dia ruim." in out
    assert "Plain sentence." in out
    assert "Frase simples." in out


def test_render_import_preview_escapes_real_rich_markup_in_front_and_back():
    cards = [
        ImportedCard(
            front="[bold]shout[/bold]", back="[red]danger[/red]"
        ),
    ]
    with ui.console.capture() as cap:
        ui.render_import_preview(cards)
    out = _strip_ansi(cap.get())
    # If escape() is called, these tags appear literally in output.
    # If escape() is NOT called, Rich parses them and they disappear from the text.
    assert "[bold]shout[/bold]" in out
    assert "[red]danger[/red]" in out
