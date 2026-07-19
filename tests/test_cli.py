from typer.testing import CliRunner

from minerator.cli import app
from minerator.config import Config, load_config, save_config
from minerator.models import Sentence, WordBlock

runner = CliRunner()


class FakeMineAnki:
    def __init__(self, model_names=None, model_fields=None, decks=None):
        self._model_names = ["Básico"] if model_names is None else model_names
        self._model_fields = model_fields or {"Básico": ["Frente", "Verso"]}
        self._decks = ["Default"] if decks is None else decks
        self.notes = []

    def ping(self):
        return True

    def model_names(self):
        return self._model_names

    def model_field_names(self, model):
        return self._model_fields.get(model, [])

    def deck_names(self):
        return self._decks

    def store_media_file(self, filename, data_b64):
        return filename

    def add_note(self, deck, model, fields, tags=None):
        self.notes.append(fields)
        return 1


def fake_ask(value):
    return type("Q", (), {"ask": lambda self: value})()


def test_check_reports_status(monkeypatch):
    monkeypatch.setattr(
        "minerator.cli.AnkiClient",
        lambda: type("C", (), {"ping": lambda self: False})(),
    )
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "Anki" in result.stdout


def test_config_show_masks_api_key(monkeypatch, tmp_path):
    cfg_file = tmp_path / "config.toml"
    save_config(Config(gemini_api_key="supersecretkey"), cfg_file)
    monkeypatch.setattr("minerator.cli.config_path", lambda: cfg_file)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "supersecretkey" not in result.stdout
    assert "gemini-2.5-flash" in result.stdout


def test_config_edit_prompt_does_not_persist_env_sourced_api_key(monkeypatch, tmp_path):
    cfg_file = tmp_path / "config.toml"
    monkeypatch.setattr("minerator.cli.config_path", lambda: cfg_file)
    monkeypatch.setenv("GEMINI_API_KEY", "secret-from-env")
    result = runner.invoke(app, ["config", "edit-prompt"])
    assert result.exit_code == 0
    assert "secret-from-env" not in cfg_file.read_text(encoding="utf-8")


def test_mine_exits_if_note_type_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setattr(
        "minerator.cli.AnkiClient", lambda: FakeMineAnki(model_names=[])
    )
    result = runner.invoke(app, ["mine"])
    assert result.exit_code == 1
    assert "Básico" in result.stdout


def test_mine_exits_if_fields_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setattr(
        "minerator.cli.AnkiClient",
        lambda: FakeMineAnki(model_fields={"Básico": ["OnlyFront"]}),
    )
    result = runner.invoke(app, ["mine"])
    assert result.exit_code == 1
    assert "Frente" in result.stdout


def test_mine_exits_cleanly_when_deck_selection_cancelled(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: FakeMineAnki())
    monkeypatch.setattr("minerator.cli.read_words", lambda: ["word1"])
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask(None))
    result = runner.invoke(app, ["mine"])
    assert result.exit_code == 0
    assert "Cancelled" in result.stdout


def test_mine_skips_word_block_with_no_sentences(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: FakeMineAnki())
    monkeypatch.setattr("minerator.cli.read_words", lambda: ["word1"])
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))

    empty_block = WordBlock(
        expression="foo",
        explanation="",
        translations=["bar"],
        grammar_class="Noun",
        sentences=[],
    )
    monkeypatch.setattr(
        "minerator.cli.GeminiConnector",
        lambda *a, **k: type("C", (), {"mine": lambda self, w, p: [empty_block]})(),
    )

    result = runner.invoke(app, ["mine"])
    assert result.exit_code == 0
    assert "no sentences" in result.stdout.lower()


def test_mine_reports_error_when_gemini_raises(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: FakeMineAnki())
    monkeypatch.setattr("minerator.cli.read_words", lambda: ["word1"])
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))

    def raise_mine(self, words, prompt):
        raise ValueError("malformed mining response")

    monkeypatch.setattr(
        "minerator.cli.GeminiConnector",
        lambda *a, **k: type("C", (), {"mine": raise_mine})(),
    )

    result = runner.invoke(app, ["mine"])
    assert result.exit_code == 1
    assert "Failed to mine" in result.stdout


def test_mine_rejects_unknown_tts_engine_before_calling_gemini(monkeypatch, tmp_path):
    cfg_file = tmp_path / "config.toml"
    save_config(Config(tts_engine="bogus"), cfg_file)
    monkeypatch.setattr("minerator.cli.config_path", lambda: cfg_file)
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: FakeMineAnki())
    monkeypatch.setattr("minerator.cli.read_words", lambda: ["word1"])
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))

    called = {"mine": False}

    def fake_mine(self, words, prompt):
        called["mine"] = True
        return []

    monkeypatch.setattr(
        "minerator.cli.GeminiConnector",
        lambda *a, **k: type("C", (), {"mine": fake_mine})(),
    )

    result = runner.invoke(app, ["mine"])
    assert result.exit_code == 1
    assert "unknown TTS engine" in result.stdout
    assert called["mine"] is False


def test_mine_creates_card_for_selected_sentence(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    anki = FakeMineAnki()
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: anki)
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))
    monkeypatch.setattr("minerator.cli.read_words", lambda: ["give up"])
    monkeypatch.setattr(
        "minerator.cli.get_engine", lambda *a, **k: None
    )  # no audio/network

    sentence = Sentence("Never give up.", "give up", "imperative")
    block = WordBlock(
        expression="give up",
        explanation="Desistir.",
        translations=["desistir"],
        grammar_class="Phrasal Verb",
        sentences=[sentence],
    )
    monkeypatch.setattr(
        "minerator.cli.GeminiConnector",
        lambda *a, **k: type("C", (), {"mine": lambda self, w, p: [block]})(),
    )
    monkeypatch.setattr("minerator.cli.select_sentences", lambda b, t: [sentence])

    result = runner.invoke(app, ["mine"])
    assert result.exit_code == 0
    assert "Cards created: 1" in result.stdout
    assert len(anki.notes) == 1


def test_mine_asks_deck_before_mining(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: FakeMineAnki())
    monkeypatch.setattr("minerator.cli.read_words", lambda: ["word1"])

    call_order = []

    def fake_questionary_select(*a, **k):
        call_order.append("deck_select")
        return fake_ask("Default")

    def fake_mine(self, words, prompt):
        call_order.append("mine")
        return []

    monkeypatch.setattr("questionary.select", fake_questionary_select)
    monkeypatch.setattr(
        "minerator.cli.GeminiConnector",
        lambda *a, **k: type("C", (), {"mine": fake_mine})(),
    )

    result = runner.invoke(app, ["mine"])
    assert result.exit_code == 0
    assert call_order == ["deck_select", "mine"]


def test_mine_stops_cleanly_when_sentence_picker_interrupted(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    anki = FakeMineAnki()
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: anki)
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))
    monkeypatch.setattr("minerator.cli.read_words", lambda: ["give up"])
    monkeypatch.setattr("minerator.cli.get_engine", lambda *a, **k: None)

    sentence = Sentence("Never give up.", "give up", "imperative")
    block = WordBlock(
        expression="give up",
        explanation="Desistir.",
        translations=["desistir"],
        grammar_class="Phrasal Verb",
        sentences=[sentence],
    )
    monkeypatch.setattr(
        "minerator.cli.GeminiConnector",
        lambda *a, **k: type("C", (), {"mine": lambda self, w, p: [block]})(),
    )

    def raise_interrupt(b, t):
        raise KeyboardInterrupt

    monkeypatch.setattr("minerator.cli.select_sentences", raise_interrupt)

    result = runner.invoke(app, ["mine"])
    assert result.exit_code == 0
    assert "Cancelled" in result.stdout
    assert len(anki.notes) == 0


def test_mine_reports_error_when_card_creation_raises(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    anki = FakeMineAnki()
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: anki)
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))
    monkeypatch.setattr("minerator.cli.read_words", lambda: ["give up"])
    monkeypatch.setattr("minerator.cli.get_engine", lambda *a, **k: None)

    sentence = Sentence("Never give up.", "give up", "imperative")
    block = WordBlock(
        expression="give up",
        explanation="Desistir.",
        translations=["desistir"],
        grammar_class="Phrasal Verb",
        sentences=[sentence],
    )
    monkeypatch.setattr(
        "minerator.cli.GeminiConnector",
        lambda *a, **k: type("C", (), {"mine": lambda self, w, p: [block]})(),
    )
    monkeypatch.setattr("minerator.cli.select_sentences", lambda b, t: [sentence])

    def raise_create_cards(*a, **k):
        raise RuntimeError("Anki connection dropped")

    monkeypatch.setattr("minerator.cli.create_cards_for_selection", raise_create_cards)

    result = runner.invoke(app, ["mine"])
    assert result.exit_code == 1
    assert "Failed to create cards" in result.stdout


def test_mine_passes_tts_engine_to_select_sentences(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    anki = FakeMineAnki()
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: anki)
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))
    monkeypatch.setattr("minerator.cli.read_words", lambda: ["give up"])

    fake_tts = object()
    monkeypatch.setattr("minerator.cli.get_engine", lambda *a, **k: fake_tts)

    sentence = Sentence("Never give up.", "give up", "imperative")
    block = WordBlock(
        expression="give up",
        explanation="Desistir.",
        translations=["desistir"],
        grammar_class="Phrasal Verb",
        sentences=[sentence],
    )
    monkeypatch.setattr(
        "minerator.cli.GeminiConnector",
        lambda *a, **k: type("C", (), {"mine": lambda self, w, p: [block]})(),
    )

    received = {}

    def fake_select_sentences(b, t):
        received["tts"] = t
        return [sentence]

    monkeypatch.setattr("minerator.cli.select_sentences", fake_select_sentences)

    result = runner.invoke(app, ["mine"])
    assert result.exit_code == 0
    assert received["tts"] is fake_tts


def fake_monotonic(values):
    it = iter(values)
    return lambda: next(it)


def test_mine_shows_elapsed_time_in_final_summary(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    anki = FakeMineAnki()
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: anki)
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))
    monkeypatch.setattr("minerator.cli.read_words", lambda: ["give up"])
    monkeypatch.setattr("minerator.cli.get_engine", lambda *a, **k: None)

    sentence = Sentence("Never give up.", "give up", "imperative")
    block = WordBlock(
        expression="give up",
        explanation="Desistir.",
        translations=["desistir"],
        grammar_class="Phrasal Verb",
        sentences=[sentence],
    )
    monkeypatch.setattr(
        "minerator.cli.GeminiConnector",
        lambda *a, **k: type("C", (), {"mine": lambda self, w, p: [block]})(),
    )
    monkeypatch.setattr("minerator.cli.select_sentences", lambda b, t: [sentence])
    monkeypatch.setattr(
        "minerator.cli.time.monotonic", fake_monotonic([1000.0, 1222.0])
    )

    result = runner.invoke(app, ["mine"])
    assert result.exit_code == 0
    assert "Cards created: 1" in result.stdout
    assert "Time spent: 3m 42s" in result.stdout


def test_mine_shows_elapsed_time_when_selection_interrupted(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    anki = FakeMineAnki()
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: anki)
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))
    monkeypatch.setattr("minerator.cli.read_words", lambda: ["give up"])
    monkeypatch.setattr("minerator.cli.get_engine", lambda *a, **k: None)

    sentence = Sentence("Never give up.", "give up", "imperative")
    block = WordBlock(
        expression="give up",
        explanation="Desistir.",
        translations=["desistir"],
        grammar_class="Phrasal Verb",
        sentences=[sentence],
    )
    monkeypatch.setattr(
        "minerator.cli.GeminiConnector",
        lambda *a, **k: type("C", (), {"mine": lambda self, w, p: [block]})(),
    )

    def raise_interrupt(b, t):
        raise KeyboardInterrupt

    monkeypatch.setattr("minerator.cli.select_sentences", raise_interrupt)
    monkeypatch.setattr(
        "minerator.cli.time.monotonic", fake_monotonic([2000.0, 2005.0])
    )

    result = runner.invoke(app, ["mine"])
    assert result.exit_code == 0
    assert "Cancelled" in result.stdout
    assert "Time spent: 5s" in result.stdout


def test_mine_shows_zero_elapsed_time_when_no_sentences_available(
    monkeypatch, tmp_path
):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: FakeMineAnki())
    monkeypatch.setattr("minerator.cli.read_words", lambda: ["word1"])
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))

    empty_block = WordBlock(
        expression="foo",
        explanation="",
        translations=["bar"],
        grammar_class="Noun",
        sentences=[],
    )
    monkeypatch.setattr(
        "minerator.cli.GeminiConnector",
        lambda *a, **k: type("C", (), {"mine": lambda self, w, p: [empty_block]})(),
    )

    result = runner.invoke(app, ["mine"])
    assert result.exit_code == 0
    assert "Time spent: 0s" in result.stdout


def test_import_exits_if_note_type_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setattr(
        "minerator.cli.AnkiClient", lambda: FakeMineAnki(model_names=[])
    )
    result = runner.invoke(app, ["import"])
    assert result.exit_code == 1
    assert "Básico" in result.stdout


def test_import_reports_nothing_to_import_on_empty_paste(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: FakeMineAnki())
    monkeypatch.setattr("minerator.cli.read_import_pairs", lambda: "")
    result = runner.invoke(app, ["import"])
    assert result.exit_code == 0
    assert "Nothing to import" in result.stdout


def test_import_reports_warnings_for_malformed_blocks(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: FakeMineAnki())
    monkeypatch.setattr("minerator.cli.read_import_pairs", lambda: "Front only line.")
    result = runner.invoke(app, ["import"])
    assert result.exit_code == 0
    assert "block 1 skipped" in result.stdout
    assert "Nothing to import" in result.stdout


def test_import_cancels_when_confirmation_declined(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    anki = FakeMineAnki()
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: anki)
    monkeypatch.setattr(
        "minerator.cli.read_import_pairs",
        lambda: "[Grammar] We had a bad day.\nNós tivemos um dia ruim.",
    )
    monkeypatch.setattr("questionary.confirm", lambda *a, **k: fake_ask(False))
    result = runner.invoke(app, ["import"])
    assert result.exit_code == 0
    assert "Cancelled" in result.stdout
    assert anki.notes == []


def test_import_exits_cleanly_when_deck_selection_cancelled(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: FakeMineAnki())
    monkeypatch.setattr("minerator.cli.read_import_pairs", lambda: "Front.\nBack.")
    monkeypatch.setattr("questionary.confirm", lambda *a, **k: fake_ask(True))
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask(None))
    result = runner.invoke(app, ["import"])
    assert result.exit_code == 0
    assert "Cancelled" in result.stdout


def test_import_creates_cards_after_confirmation(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    anki = FakeMineAnki()
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: anki)
    monkeypatch.setattr(
        "minerator.cli.read_import_pairs",
        lambda: "[Grammar] We had a bad day.\nNós tivemos um dia ruim.",
    )
    monkeypatch.setattr("questionary.confirm", lambda *a, **k: fake_ask(True))
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))
    monkeypatch.setattr("minerator.cli.get_engine", lambda *a, **k: None)

    result = runner.invoke(app, ["import"])
    assert result.exit_code == 0
    assert "Cards created: 1" in result.stdout
    assert len(anki.notes) == 1
    assert anki.notes[0]["Frente"] == "[Grammar] We had a bad day."
    assert anki.notes[0]["Verso"] == "Nós tivemos um dia ruim."


def test_import_reports_error_when_card_creation_raises(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    anki = FakeMineAnki()
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: anki)
    monkeypatch.setattr(
        "minerator.cli.read_import_pairs",
        lambda: "[Grammar] We had a bad day.\nNós tivemos um dia ruim.",
    )
    monkeypatch.setattr("questionary.confirm", lambda *a, **k: fake_ask(True))
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))
    monkeypatch.setattr("minerator.cli.get_engine", lambda *a, **k: None)

    def raise_create_imported_cards(*a, **k):
        raise RuntimeError("Anki connection dropped")

    monkeypatch.setattr(
        "minerator.cli.create_imported_cards", raise_create_imported_cards
    )

    result = runner.invoke(app, ["import"])
    assert result.exit_code == 1
    assert "Failed to create cards" in result.stdout


def test_import_stops_cleanly_when_card_creation_interrupted(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    anki = FakeMineAnki()
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: anki)
    monkeypatch.setattr(
        "minerator.cli.read_import_pairs",
        lambda: "[Grammar] We had a bad day.\nNós tivemos um dia ruim.",
    )
    monkeypatch.setattr("questionary.confirm", lambda *a, **k: fake_ask(True))
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))
    monkeypatch.setattr("minerator.cli.get_engine", lambda *a, **k: None)

    def raise_interrupt(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr("minerator.cli.create_imported_cards", raise_interrupt)

    result = runner.invoke(app, ["import"])
    assert result.exit_code == 0
    assert "Cancelled" in result.stdout
    assert len(anki.notes) == 0


def test_config_toggle_strip_tags_flips_and_persists(monkeypatch, tmp_path):
    cfg_file = tmp_path / "config.toml"
    monkeypatch.setattr("minerator.cli.config_path", lambda: cfg_file)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = runner.invoke(app, ["config", "toggle-strip-tags"])
    assert result.exit_code == 0
    assert "disabled" in result.stdout
    assert load_config(cfg_file).strip_bracket_tags is False

    result = runner.invoke(app, ["config", "toggle-strip-tags"])
    assert result.exit_code == 0
    assert "enabled" in result.stdout
    assert load_config(cfg_file).strip_bracket_tags is True
