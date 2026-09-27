from __future__ import annotations

from dataclasses import fields

from .core.config import Config


def config_from_dict(data: dict) -> Config:
    known = {f.name for f in fields(Config)}
    values = {k: v for k, v in data.items() if k in known}
    key = values.get("gemini_api_key")
    # A blank or non-string key (e.g. a number typed without quotes in the
    # config editor) is treated as missing, so the wizard says so plainly.
    if not isinstance(key, str) or not key.strip():
        values["gemini_api_key"] = None
    return Config(**values)
