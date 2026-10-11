from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
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
    # Set when every source stopped: the remaining cards use the system voice.
    stopped: str | None = None
    # Sources that stopped while a later one took over the rest of the run.
    handovers: list[str] = field(default_factory=list)


def _unique(texts: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(text for text in texts if text))


def record_all(
    recorders: Sequence[Recorder],
    texts: Iterable[str],
    on_progress: Callable[[int, int], None] | None = None,
) -> RecordingRun:
    """Record each sentence with the first source in the chain that can.

    A sentence one source fails on goes to the next. A source failure (the
    service is down, the key is bad, the quota is spent) takes that source
    out of the run, so later sentences go straight to the next one; once
    every source has stopped, the rest are left to the system voice.
    """
    unique = _unique(texts)
    recordings: dict[str, Recording] = {}
    failures: dict[str, str] = {}
    stops: dict[int, str] = {}
    handovers: list[str] = []
    all_stopped: list[str] = []

    for index, text in enumerate(unique):
        reasons: list[str] = []
        for position, recorder in enumerate(recorders):
            if position in stops:
                continue
            try:
                data = recorder.record(text)
            except AudioError as exc:
                if not exc.source_down:
                    reasons.append(str(exc))
                    continue
                stops[position] = str(exc)
            except Exception as exc:
                # A bug or an unforeseen response must cost the audio, never
                # the cards: take this source out and let the chain go on.
                stops[position] = f"unexpected error: {exc}"
            else:
                name = media_name(recorder.source, recorder.voice, text)
                recordings[text] = Recording(name, data)
                break
            backup = next(
                (r for p, r in enumerate(recorders) if p > position and p not in stops),
                None,
            )
            if backup is not None:
                handovers.append(
                    f"{stops[position]}; later sentences were recorded with "
                    f"{backup.name}."
                )
        else:
            if reasons:
                failures[text] = "; ".join(reasons)
            else:
                all_stopped.append(text)
        if on_progress is not None:
            on_progress(index + 1, len(unique))

    stopped = "; ".join(stops[p] for p in sorted(stops)) if all_stopped else None
    for text in all_stopped:
        failures[text] = stopped or ""
    if stopped is not None:
        # Every source stopped: the stop note explains it, the handovers
        # would only repeat the reasons.
        handovers = []
    return RecordingRun(recordings, failures, stopped, handovers)


def failed_run(texts: Iterable[str], reason: str) -> RecordingRun:
    return RecordingRun(
        failures={text: reason for text in _unique(texts)}, stopped=reason
    )


def run_notes(run: RecordingRun | None) -> list[str]:
    if run is None:
        return []
    notes = list(run.handovers)
    if run.stopped is not None:
        notes.append(
            f"Audio recording stopped: {run.stopped}. "
            "Cards without a recording use the system voice."
        )
    return notes
