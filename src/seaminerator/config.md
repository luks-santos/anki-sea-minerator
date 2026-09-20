# Sea Minerator

- `gemini_api_key` — your Google AI Studio API key. Stored in plain text.
- `model` — Gemini model id, e.g. `gemini-2.5-flash`.
- `default_deck` — deck pre-selected in the wizard. Blank means no default.
- `tts_lang` — language passed to Anki's `{{tts}}` tag, e.g. `en_US`.
  Changing it rewrites the note type template, which affects existing cards.
- `highlight_color` — CSS color for the studied expression on the front.
- `prompt_path` — path to a file overriding the built-in mining prompt.
  Blank uses the built-in prompt.
