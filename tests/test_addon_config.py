from seaminerator.addon_config import config_from_dict


def test_config_from_dict_maps_known_keys():
    cfg = config_from_dict(
        {
            "gemini_api_key": "k",
            "model": "gemini-2.5-flash",
            "default_deck": "English",
            "tts_lang": "en_US",
            "highlight_color": "#ff0000",
            "prompt_path": "/tmp/p.txt",
        }
    )
    assert cfg.gemini_api_key == "k"
    assert cfg.default_deck == "English"
    assert cfg.highlight_color == "#ff0000"


def test_config_from_dict_uses_defaults_for_missing_keys():
    cfg = config_from_dict({})
    assert cfg.model == "gemini-2.5-flash"
    assert cfg.tts_lang == "en_US"
    assert cfg.gemini_api_key is None


def test_config_from_dict_ignores_unknown_keys():
    cfg = config_from_dict({"nonsense": 1, "model": "gemini-3-pro"})
    assert cfg.model == "gemini-3-pro"


def test_config_from_dict_treats_blank_api_key_as_missing():
    assert config_from_dict({"gemini_api_key": ""}).gemini_api_key is None
    assert config_from_dict({"gemini_api_key": "  "}).gemini_api_key is None
