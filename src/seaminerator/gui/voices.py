from __future__ import annotations

from anki.sound import TTSTag
from aqt.sound import av_player

PREVIEW_TEXT = "This is how your cards will sound."


def installed_voices() -> list[tuple[str, str]]:
    """(name, lang) of every usable system voice Anki can speak with here.

    Only Anki's own players are asked: a voice another add-on registers (like
    AwesomeTTS's) needs that add-on's own setup and doesn't exist on phones.
    """
    # Mirrors aqt.tts.all_tts_voices, which is not part of Anki's add-on API;
    # if a later version breaks this, the voice box falls back to plain text.
    try:
        voices = []
        for player in av_player.players:
            if not type(player).__module__.startswith("aqt."):
                continue
            getter = getattr(player, "validated_voices", None) or getattr(
                player, "voices", None
            )
            if getter:
                voices.extend(getter())
        return [(voice.name, voice.lang) for voice in voices if not voice.unavailable()]
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
