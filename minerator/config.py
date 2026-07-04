from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

import tomli_w
from platformdirs import user_config_dir

APP_NAME = "anki-sea-minerator"


@dataclass
class Config:
    gemini_api_key: str | None = None
    model: str = "gemini-2.5-flash"
    default_deck: str = ""
    note_type: str = "Básico"
    front_field: str = "Frente"
    back_field: str = "Verso"
    tts_engine: str = "edge"
    tts_voice: str = "en-US-EmmaNeural"
    highlight_color: str = "#2563eb"
    prompt_path: str = ""


def config_path() -> Path:
    return Path(user_config_dir(APP_NAME)) / "config.toml"


def load_config(path: Path | None = None, use_env: bool = True) -> Config:
    path = path or config_path()
    data: dict = {}
    if path.is_file():
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    known = {f: data[f] for f in Config().__dict__ if f in data}
    cfg = Config(**known)
    if use_env:
        env_key = os.environ.get("GEMINI_API_KEY")
        if env_key:
            cfg.gemini_api_key = env_key
    return cfg


def save_config(cfg: Config, path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {k: v for k, v in asdict(cfg).items() if v is not None}
    with path.open("wb") as fh:
        tomli_w.dump(data, fh)
