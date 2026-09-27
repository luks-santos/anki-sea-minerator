# Sea Minerator

Use **Tools → Sea Minerator settings…** (or the Config button here) to pick a
provider, paste its API key, choose a model and test the connection. Editing
this JSON directly is only needed for `prompt_path`.

- `provider` — `gemini`, `openai` (OpenAI and compatible services such as
  OpenRouter or Groq, with a model that supports `json_schema` structured
  outputs), `anthropic`, or `local` (Ollama, LM Studio).
- `providers` — one block per provider with `api_key`, `model` and
  `base_url`. Keys are stored in plain text.
- `default_deck` — deck pre-selected in the wizard. Blank means no default.
- `tts_lang` — language passed to Anki's `{{tts}}` tag, e.g. `en_US`.
  Changing it rewrites the note type template, which affects existing cards.
- `highlight_color` — CSS color for the studied expression on the front.
- `prompt_path` — path to a file overriding the built-in mining prompt.
  Blank uses the built-in prompt. The grammar class and topic rules are always
  appended to it, and the response format is fixed by the add-on.
