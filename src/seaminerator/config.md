# Sea Minerator

Use **Tools → Sea Minerator settings…** (or the Config button here) to pick
your native language, edit the mining prompt, pick a provider, paste its API
key, choose a model and test the connection. Every option below can be set
there; editing this JSON directly is never required.

- `native_language` — your language, as a code: `pt-BR`, `pt-PT`, `es`, `fr`,
  `de`, `it`, `nl`, `pl`, `ru`, `uk`, `tr`, `ar`, `hi`, `id`, `vi`, `th`,
  `ja`, `ko`, `zh-CN` or `zh-TW`. Explanations and translations of mined words
  are written in it. Blank until chosen; the mining screen asks for it.
- `prompts` — mining prompts you edited, by language code, e.g.
  `{"es": "…"}`. A language without an entry uses its default prompt: a tuned
  one for `pt-BR`, a generic one for the others. The response format and the
  grammar class and topic rules are always added after it.
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
