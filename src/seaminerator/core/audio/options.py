from __future__ import annotations

AUDIO_SOURCES: tuple[str, ...] = ("system", "google", "gemini")

SOURCE_LABELS: dict[str, str] = {
    "system": "System voice",
    "google": "Google Translate (free, unofficial)",
    "gemini": "Gemini (uses your Gemini key)",
}

# translate.google.<code> picks the English accent. "com" is left out: it
# follows the network's location, so the accent would change with the user.
GOOGLE_ACCENTS: dict[str, str] = {
    "us": "United States",
    "co.uk": "United Kingdom",
    "com.au": "Australia",
    "ca": "Canada",
    "co.in": "India",
    "ie": "Ireland",
    "co.za": "South Africa",
}

# GA since 2026-09-22 and free on the free tier; the 2.5 and 3.1 TTS models
# shut down on 2026-11-17.
GEMINI_TTS_MODEL = "gemini-3.8-flash-lite-tts"

GEMINI_VOICES: tuple[str, ...] = (
    "Zephyr",
    "Puck",
    "Charon",
    "Kore",
    "Fenrir",
    "Leda",
    "Orus",
    "Aoede",
    "Callirrhoe",
    "Autonoe",
    "Enceladus",
    "Iapetus",
    "Umbriel",
    "Algieba",
    "Despina",
    "Erinome",
    "Algenib",
    "Rasalgethi",
    "Laomedeia",
    "Achernar",
    "Alnilam",
    "Schedar",
    "Gacrux",
    "Pulcherrima",
    "Achird",
    "Zubenelgenubi",
    "Vindemiatrix",
    "Sadachbia",
    "Sadaltager",
    "Sulafat",
)

GEMINI_KEY_MESSAGE = (
    "Gemini audio needs a Gemini API key (set it under Provider: Gemini)."
)
