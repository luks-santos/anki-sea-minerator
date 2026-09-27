from __future__ import annotations

from anki.sound import TTSTag
from aqt.sound import av_player

PREVIEW_TEXT = "This is how your cards will sound."


def installed_voices() -> list[tuple[str, str]]:
    """(name, lang) of every usable voice Anki can speak with here."""
    # all_tts_voices is not part of Anki's add-on API; if a later version
    # moves or breaks it, the voice box falls back to plain text entry.
    try:
        from aqt.tts import all_tts_voices

        return [
            (voice.name, voice.lang)
            for voice in all_tts_voices()
            if not voice.unavailable()
        ]
    except Exception:
        return []


def preview(lang: str, voices: tuple[str, ...], speed: float) -> None:
    # The same tag a card's {{tts}} produces, so the preview picks the voice
    # the way the reviewer will.
    tag = TTSTag(
        field_text=PREVIEW_TEXT,
        lang=lang,
        voices=list(voices),
        speed=speed,
        other_args=[],
    )
    av_player.play_tags([tag])
