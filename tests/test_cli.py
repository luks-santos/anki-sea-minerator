from typer.testing import CliRunner

from minerator.cli import app

runner = CliRunner()


def test_check_reports_status(monkeypatch):
    monkeypatch.setattr("minerator.cli.AnkiClient", lambda: type("C", (), {"ping": lambda self: False})())
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "Anki" in result.stdout


def test_config_show_masks_api_key(monkeypatch, tmp_path):
    from minerator.config import Config, save_config

    cfg_file = tmp_path / "config.toml"
    save_config(Config(gemini_api_key="supersecretkey"), cfg_file)
    monkeypatch.setattr("minerator.cli.config_path", lambda: cfg_file)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "supersecretkey" not in result.stdout
    assert "gemini-2.5-flash" in result.stdout
