from minerator.config import Config


def test_config_defaults():
    cfg = Config()
    assert cfg.gemini_api_key is None
    assert cfg.model == "gemini-2.5-flash"
    assert cfg.tts_lang == "en_US"
    assert cfg.highlight_color == "#2563eb"
    assert cfg.default_deck == ""
    assert cfg.prompt_path == ""


def test_config_accepts_overrides():
    cfg = Config(gemini_api_key="k", tts_lang="pt_BR", highlight_color="#ff0000")
    assert cfg.gemini_api_key == "k"
    assert cfg.tts_lang == "pt_BR"
    assert cfg.highlight_color == "#ff0000"
