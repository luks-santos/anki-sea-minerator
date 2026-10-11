from __future__ import annotations

import os
import shutil
import subprocess

from anki.utils import tmpfile

from ..core.audio.base import AudioError

LAME_MISSING = (
    "Gemini audio needs LAME, which Anki bundles on Windows and macOS; "
    "on Linux, install the lame package."
)


def _lame_command(wav: str, mp3: str) -> tuple[list[str], dict[str, str]]:
    # Anki's own recorder finds its bundled LAME this way. _packagedCmd is
    # private, so callers turn any failure here into a fallback.
    from aqt.sound import _packagedCmd

    return _packagedCmd(["lame", wav, mp3, "--noreplaygain", "--quiet"])


def lame_available() -> bool:
    try:
        cmd, env = _lame_command("in.wav", "out.mp3")
    except Exception:
        return False
    return (
        os.path.isfile(cmd[0]) or shutil.which(cmd[0], path=env.get("PATH")) is not None
    )


def encode_mp3(wav: bytes) -> bytes:
    wav_path = tmpfile(suffix=".wav")
    mp3_path = tmpfile(suffix=".mp3")
    try:
        with open(wav_path, "wb") as file:
            file.write(wav)
        from aqt.utils import startup_info

        cmd, env = _lame_command(wav_path, mp3_path)
        result = subprocess.run(
            cmd, env=env, startupinfo=startup_info(), capture_output=True, timeout=60
        )
        if result.returncode != 0:
            raise AudioError(
                f"LAME failed (exit {result.returncode})", source_down=True
            )
        with open(mp3_path, "rb") as file:
            return file.read()
    except AudioError:
        raise
    except Exception as exc:
        raise AudioError(f"{LAME_MISSING} ({exc})", source_down=True) from exc
    finally:
        for path in (wav_path, mp3_path):
            try:
                os.remove(path)
            except OSError:
                pass
