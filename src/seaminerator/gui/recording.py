from __future__ import annotations

from collections.abc import Callable, Sequence

from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import QWidget

from ..core.audio.recording import RecordingRun, failed_run, record_all
from ..core.audio.registry import build_recorder
from ..core.config import Config, ConfigError
from .mp3 import encode_mp3


def record_then(
    parent: QWidget,
    cfg: Config,
    texts: Sequence[str],
    on_done: Callable[[RecordingRun | None], None],
) -> None:
    """Record the sentences for a recorded audio source, then call `on_done`.

    `on_done` gets None for the system voice (nothing to record). Recording
    runs without the collection, so Anki stays usable while it waits on the
    network; the caller then creates every card in one CollectionOp.
    """
    try:
        recorder = build_recorder(cfg, encode_mp3)
    except ConfigError as exc:
        on_done(failed_run(texts, str(exc)))
        return
    if recorder is None:
        on_done(None)
        return

    def progress(done: int, total: int) -> None:
        mw.taskman.run_on_main(
            lambda: mw.progress.update(
                label=f"Recording audio {done}/{total}…", value=done, max=total
            )
        )

    QueryOp(
        parent=parent,
        op=lambda _col: record_all(recorder, texts, progress),
        success=on_done,
    ).failure(
        lambda exc: on_done(failed_run(texts, f"recording failed: {exc}"))
    ).without_collection().with_progress("Recording audio…").run_in_background()
