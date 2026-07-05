from typer.testing import CliRunner

from minerator.cli import _read_words, app
from minerator.config import Config, save_config
from minerator.models import WordBlock

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
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask(None))
    result = runner.invoke(app, ["mine"], input="word1\n\n")
    assert result.exit_code == 0
    assert "Cancelled" in result.stdout


def test_mine_skips_word_block_with_no_sentences(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: FakeMineAnki())
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

    result = runner.invoke(app, ["mine"], input="word1\n\n")
    assert result.exit_code == 0
    assert "no sentences" in result.stdout.lower()


def test_mine_reports_error_when_gemini_raises(monkeypatch, tmp_path):
    monkeypatch.setattr("minerator.cli.config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: FakeMineAnki())
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))

    def raise_mine(self, words, prompt):
        raise ValueError("malformed mining response")

    monkeypatch.setattr(
        "minerator.cli.GeminiConnector",
        lambda *a, **k: type("C", (), {"mine": raise_mine})(),
    )

    result = runner.invoke(app, ["mine"], input="word1\n\n")
    assert result.exit_code == 1
    assert "Failed to mine" in result.stdout


def test_mine_rejects_unknown_tts_engine_before_calling_gemini(monkeypatch, tmp_path):
    cfg_file = tmp_path / "config.toml"
    save_config(Config(tts_engine="bogus"), cfg_file)
    monkeypatch.setattr("minerator.cli.config_path", lambda: cfg_file)
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: FakeMineAnki())
    monkeypatch.setattr("questionary.select", lambda *a, **k: fake_ask("Default"))

    called = {"mine": False}

    def fake_mine(self, words, prompt):
        called["mine"] = True
        return []

    monkeypatch.setattr(
        "minerator.cli.GeminiConnector",
        lambda *a, **k: type("C", (), {"mine": fake_mine})(),
    )

    result = runner.invoke(app, ["mine"], input="word1\n\n")
    assert result.exit_code == 1
    assert "unknown TTS engine" in result.stdout
    assert called["mine"] is False


def test_read_words_stops_gracefully_on_eof(monkeypatch):
    lines = iter(["word1", "word2"])

    def fake_input():
        try:
            return next(lines)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr("builtins.input", fake_input)
    assert _read_words() == ["word1", "word2"]
