from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from .base import AudioError, Recorder, media_name


@dataclass(frozen=True)
class Recording:
    name: str
    data: bytes


@dataclass(frozen=True)
class RecordingRun:
    # Keyed by the spoken text, so cards sharing a sentence share a file.
    recordings: dict[str, Recording] = field(default_factory=dict)
    failures: dict[str, str] = field(default_factory=dict)
    stopped: str | None = None


def _unique(texts: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(text for text in texts if text))


def record_all(
    recorder: Recorder,
    texts: Iterable[str],
    on_progress: Callable[[int, int], None] | None = None,
) -> RecordingRun:
    unique = _unique(texts)
    recordings: dict[str, Recording] = {}
    failures: dict[str, str] = {}
    stopped: str | None = None
    for index, text in enumerate(unique):
        if stopped is not None:
            failures[text] = stopped
            continue
        try:
            data = recorder.record(text)
        except AudioError as exc:
            failures[text] = str(exc)
            if exc.source_down:
                stopped = str(exc)
        except Exception as exc:
            # A bug or an unforeseen response must cost the audio, never the
            # cards: stop asking and let every card use the system voice.
            stopped = f"unexpected error: {exc}"
            failures[text] = stopped
        else:
            name = media_name(recorder.source, recorder.voice, text)
            recordings[text] = Recording(name, data)
        if on_progress is not None:
            on_progress(index + 1, len(unique))
    return RecordingRun(recordings, failures, stopped)


def failed_run(texts: Iterable[str], reason: str) -> RecordingRun:
    return RecordingRun(
        failures={text: reason for text in _unique(texts)}, stopped=reason
    )


def stopped_note(run: RecordingRun | None) -> str | None:
    if run is None or run.stopped is None:
        return None
    return (
        f"Audio recording stopped: {run.stopped}. "
        "Cards without a recording use the system voice."
    )
