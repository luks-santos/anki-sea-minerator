from minerator.config import Config, load_config, save_config


def test_defaults_match_spec():
    cfg = Config()
    assert cfg.model == "gemini-2.5-flash"
    assert cfg.tts_engine == "edge"
    assert cfg.tts_voice == "en-US-AriaNeural"
    assert cfg.note_type == "Básico"
    assert cfg.front_field == "Frente"
    assert cfg.back_field == "Verso"
    assert cfg.highlight_color == "#2563eb"


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "config.toml"
    cfg = Config(gemini_api_key="k123", default_deck="English::Mining")
    save_config(cfg, path)
    loaded = load_config(path)
    assert loaded.gemini_api_key == "k123"
    assert loaded.default_deck == "English::Mining"
    assert loaded.model == "gemini-2.5-flash"


def test_load_missing_file_returns_defaults(tmp_path):
    cfg = load_config(tmp_path / "absent.toml")
    assert cfg == Config()


def test_env_overrides_api_key(tmp_path, monkeypatch):
    path = tmp_path / "config.toml"
    save_config(Config(gemini_api_key="from-file"), path)
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    assert load_config(path).gemini_api_key == "from-env"
