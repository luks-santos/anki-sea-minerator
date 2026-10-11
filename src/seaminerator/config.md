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
  dialog lists this computer's voices and can preview them. `AwesomeTTS` is
  dropped: other add-ons' voices are not supported.
- `tts_speed` — speaking speed from `0.5` to `2.0`; `1.0` is normal.
- `highlight_color` — CSS color for the studied expression on the front.
- `audio` — where card audio comes from:
  - `source`: `system` (default: the device's voices through `{{tts}}`),
    `google` (Google Translate, an unofficial endpoint) or `gemini` (Gemini
    TTS with the Gemini provider's API key). The recorded sources store an
    MP3 per new card in its `Audio` field; when recording fails, the card
    uses the system voice.
  - `google.accent`: `us`, `co.uk`, `com.au`, `ca`, `co.in`, `ie` or `co.za`.
  - `gemini.voice` (e.g. `Kore`, `Puck`) and `gemini.model` (default
    `gemini-3.8-flash-lite-tts`; the 2.5/3.1 TTS models stop working on
    2026-11-17). Gemini audio needs LAME: Anki bundles it on Windows and
    macOS; on Linux, install the `lame` package.
  - Choosing a recorded source adds an `Audio` field to an existing Sea
    Minerator note type, which makes the next sync a one-time full sync. The
    settings dialog asks first; setting `source` here by hand adds the field
    on the next mining or import without asking.
