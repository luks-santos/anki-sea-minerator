from __future__ import annotations

import hashlib
import html
import re
from typing import Protocol

_LABEL_PREFIX = re.compile(r"^\s*\[[^\[\]]+\]\s*")
_TAG = re.compile(r"<[^>]*>")


class AudioError(Exception):
    def __init__(self, message: str, *, source_down: bool) -> None:
        super().__init__(message)
        # True when the next sentences would fail the same way (service
        # down, blocked, bad key, quota), so recording stops for this run.
        self.source_down = source_down


class Recorder(Protocol):
    source: str
    # Shown to the user, e.g. in the note about which source took over.
    name: str
    # What the recording sounds like (accent or voice name); part of the
    # media file name, so a different voice never reuses another's file.
    voice: str

    def record(self, text: str) -> bytes: ...


def speech_text(raw: str, *, strip_label: bool = False) -> str:
    text = _LABEL_PREFIX.sub("", raw, count=1) if strip_label else raw
    text = html.unescape(_TAG.sub(" ", text))
    return " ".join(text.split())


def media_name(source: str, voice: str, text: str) -> str:
    digest = hashlib.sha1(f"{source}|{voice}|{text}".encode()).hexdigest()[:20]
    return f"sea-minerator-{digest}.mp3"
