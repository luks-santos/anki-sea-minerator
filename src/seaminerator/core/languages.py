from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NativeLanguage:
    code: str
    # Shown in the combo boxes, in the language itself.
    label: str
    # Written into the mining prompt template.
    english_name: str


_LANGUAGES = (
    NativeLanguage("pt-BR", "Português (Brasil)", "Brazilian Portuguese"),
    NativeLanguage("pt-PT", "Português (Portugal)", "European Portuguese"),
    NativeLanguage("es", "Español", "Spanish"),
    NativeLanguage("fr", "Français", "French"),
    NativeLanguage("de", "Deutsch", "German"),
    NativeLanguage("it", "Italiano", "Italian"),
    NativeLanguage("nl", "Nederlands", "Dutch"),
    NativeLanguage("pl", "Polski", "Polish"),
    NativeLanguage("ru", "Русский", "Russian"),
    NativeLanguage("uk", "Українська", "Ukrainian"),
    NativeLanguage("tr", "Türkçe", "Turkish"),
    NativeLanguage("ar", "العربية", "Arabic"),
    NativeLanguage("hi", "हिन्दी", "Hindi"),
    NativeLanguage("id", "Bahasa Indonesia", "Indonesian"),
    NativeLanguage("vi", "Tiếng Việt", "Vietnamese"),
    NativeLanguage("th", "ไทย", "Thai"),
    NativeLanguage("ja", "日本語", "Japanese"),
    NativeLanguage("ko", "한국어", "Korean"),
    NativeLanguage("zh-CN", "简体中文", "Simplified Chinese"),
    NativeLanguage("zh-TW", "繁體中文", "Traditional Chinese"),
)

# The language explanations and translations are written in. The studied
# language is always English, so English itself is not offered.
NATIVE_LANGUAGES: dict[str, NativeLanguage] = {
    language.code: language for language in _LANGUAGES
}
