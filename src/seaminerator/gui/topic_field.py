from __future__ import annotations

from dataclasses import replace

from aqt import mw
from aqt.qt import QWidget
from aqt.utils import askUser, showWarning

from ..addon_config import with_topic_badge
from ..anki.notetype import ensure_notetype, has_topic_field
from ..core.config import Config

ADDON = __name__.split(".")[0]

TOPIC_FIELD_QUESTION = (
    "Cards can show their grammar subject (Present perfect, Modal verbs…) as a "
    "badge above the sentence. That needs a Topic field in the Sea Minerator "
    "note type.\n\n"
    "Adding it changes the collection's structure, so the next sync will ask "
    "for a one-time full sync: sync your other devices first, then choose "
    "Upload here. Existing cards are not changed.\n\n"
    "Add the field now? If not, you can turn the badge on later in Sea "
    "Minerator settings."
)


def prepare_topic_field(parent: QWidget, cfg: Config, wanted: bool) -> Config:
    """The config to create cards with, after asking for the Topic field if needed.

    Adding a field to an existing note type forces a full sync, so it is only
    added on a yes. A no is stored (the badge turns off, Settings turns it
    back on) and the cards are created without a Topic.
    """
    if not cfg.topic_badge or not wanted or has_topic_field(mw.col):
        return cfg
    if not askUser(TOPIC_FIELD_QUESTION, parent=parent):
        stored = mw.addonManager.getConfig(ADDON) or {}
        mw.addonManager.writeConfig(ADDON, with_topic_badge(stored, False))
        return replace(cfg, topic_badge=False)
    try:
        ensure_notetype(
            mw.col,
            cfg.tts_lang,
            cfg.tts_voices,
            cfg.tts_speed,
            audio=cfg.audio.source != "system",
            topic=True,
        )
    except Exception as exc:
        showWarning(
            f"Could not add the Topic field: {exc}", parent=parent, textFormat="plain"
        )
        return replace(cfg, topic_badge=False)
    return cfg
