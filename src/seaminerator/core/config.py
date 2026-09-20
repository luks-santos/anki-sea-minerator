from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Config:
    gemini_api_key: str | None = None
    model: str = "gemini-2.5-flash"
    default_deck: str = ""
    tts_lang: str = "en_US"
    highlight_color: str = "#2563eb"
    prompt_path: str = ""
