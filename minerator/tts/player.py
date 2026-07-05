from __future__ import annotations

import os
import tempfile

import playsound3


def play_audio(data: bytes) -> None:
    fd, path = tempfile.mkstemp(suffix=".mp3")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        playsound3.playsound(path)
    finally:
        os.remove(path)
