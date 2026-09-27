# Sea Minerator

Use **Tools → Sea Minerator settings…** (or the Config button here) to pick a
provider, paste its API key, choose a model and test the connection. Editing
this JSON directly is only needed for `prompt_path`.

- `provider` — `gemini`, `openai` (OpenAI and compatible services such as
  OpenRouter or Groq, with a model that supports `json_schema` structured
  outputs), `anthropic`, or `local` (Ollama at `http://localhost:11434/v1`,
  the default; LM Studio at `http://localhost:1234/v1`).
- `providers` — one block per provider with `api_key`, `model` and
  `base_url`. Keys are stored in plain text.
- `default_deck` — deck pre-selected in the wizard. Blank means no default.
- `tts_lang` — language passed to Anki's `{{tts}}` tag, e.g. `en_US`.
  Changing it rewrites the note type template, which affects existing cards.
- `tts_voices` — voices for `{{tts}}` in order of preference, e.g.
  `["Microsoft_Zira", "Apple_Samantha"]`; each device uses the first one it
  has. Empty uses the device's first voice for the language. The settings
  dialog lists this computer's voices and can preview them.
- `tts_speed` — speaking speed from `0.5` to `2.0`; `1.0` is normal.
- `highlight_color` — CSS color for the studied expression on the front.
- `prompt_path` — path to a file overriding the built-in mining prompt.
  Blank uses the built-in prompt. The grammar class and topic rules are always
  appended to it, and the response format is fixed by the add-on.
