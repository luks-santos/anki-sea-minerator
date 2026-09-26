# Sea Minerator

An [Anki](https://apps.ankiweb.net/) add-on that mines a list of English
vocabulary into flashcards, powered by Google Gemini.

## What it does

You open `Tools → Mine vocabulary…` in Anki, paste a "list of the day" (one
word or expression per line), and pick a target deck. Gemini returns
structured data for each item — a short explanation, a grammar class tag,
translations, and example sentences with the mined expression marked and
their grammar topic tags. You
review the sentences and check off which ones should become cards. On
confirmation, Sea Minerator creates one Anki note per selected sentence, all
under a single undo step, and shows a summary of what was created.

Everything runs inside Anki's own process: there is no external server, no
AnkiConnect, and no CLI. The add-on talks to Gemini directly over HTTPS and
writes notes straight into your collection.

## How a card looks

Cards use their own note type, **Sea Minerator**, created automatically the
first time you mine:

- **Front:** the example sentence, with the mined expression highlighted in
  color, plus an inline `{{tts}}` tag that plays the sentence aloud.
- **Back:** the expression, its translations, and its grammar class (e.g.
  "Phrasal verb").
- **Tags:** `anki-sea-minerator`, one grammar class (`noun`, `verb`,
  `phrasal-verb`, `idiom`, `expression`…) and the grammar topics the sentence
  exercises (`past-simple`, `present-perfect`…). Topics reuse the tags that
  already exist in your collection; a new one is created only when none fits.
  The class can be changed per word in the review screen.

## Install

1. Download `sea-minerator.ankiaddon` (see [Building from source](#building-from-source)
   if you're building it yourself rather than getting a released copy).
2. In Anki: `Tools → Add-ons → Install from file…`, pick the `.ankiaddon`
   file, then restart Anki.

## Setup

1. Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/).
2. In Anki: `Tools → Add-ons`, select **Sea Minerator**, click **Config**, and
   paste the key into `gemini_api_key`. Save.

The config screen (Anki's built-in JSON editor) also lets you set:

- `model` — the Gemini model id, e.g. `gemini-2.5-flash`.
- `default_deck` — the deck pre-selected in the wizard.
- `tts_lang` — the language passed to Anki's `{{tts}}` tag, e.g. `en_US`.
  Changing it rewrites the note type's template, which affects existing cards.
- `highlight_color` — the CSS color used for the studied expression.
- `prompt_path` — a file overriding the built-in mining prompt, if you want to
  customize how Gemini is instructed.

See `src/seaminerator/config.md` for the full reference.

## Usage

`Tools → Mine vocabulary…` opens the wizard:

1. Paste your list and choose a deck, then click **Mine**.
2. Review each word's sentences and check the ones you want as cards.
3. Click **Create cards**. Anki creates them as one batch, undoable in one
   step (`Edit → Undo`).
4. The summary screen shows how many cards were created and any warnings
   (for example, a sentence where the expression text couldn't be located to
   highlight).

## Audio: what `{{tts}}` can and can't do

Sea Minerator does not generate or bundle any audio files. The front of each
card contains Anki's native `{{tts}}` tag, which asks whatever is running
Anki to speak the sentence using **the operating system's own
text-to-speech voices** at review time. That has real consequences worth
knowing before you rely on it:

- **Requires Anki 2.1.20+ on desktop**, AnkiDroid 2.17+, or AnkiMobile
  2.0.56+. Older clients will show the tag literally instead of speaking it.
- **No support on plain Linux.** Desktop TTS depends on the OS having a
  speech engine installed and configured (macOS and Windows ship one;
  Anki's `{{tts}}` support does not extend to typical bare Linux setups
  without extra configuration you'd have to do yourself).
- **Voice quality and availability depend on what's installed on each
  device.** The same card can sound different — or silent — on different
  computers or phones, because it's playing through whatever local voices
  exist there, not a bundled recording.
- **Probably does not work on AnkiWeb.** AnkiWeb's browser-based reviewer
  does not reliably support `{{tts}}`; treat cards as desktop/mobile-app
  only if audio matters to you.

If your study setup depends on hearing every card reliably in the browser or
on Linux, this add-on's audio will disappoint you — highlighting, the mined
content, and the note type still work regardless, but the sentence won't
always be read aloud.

## Building from source

Only one runtime dependency, `httpx`, and its own transitive dependencies are
used, and they are vendored into the repo (`src/seaminerator/_vendor/`)
rather than installed at runtime — an `.ankiaddon` has no install step, so
whatever the add-on imports has to ship inside the zip. `_vendor/` is
committed on purpose for that reason; `dist/`, the built zip, is not (see
`.gitignore`).

```bash
bash scripts/vendor.sh   # (re)populate src/seaminerator/_vendor/
bash scripts/build.sh    # produce dist/sea-minerator.ankiaddon
```

Only `httpx` and its transitive dependencies may be vendored, and only
because they're pure Python — no package with C extensions belongs in
`_vendor/`, since the add-on ships as one platform-independent zip. See the
comments at the top of `scripts/vendor.sh` if you ever change the
dependency.

## Development

See `docs/development.md` for running the add-on straight from this repo
(without building a `.ankiaddon`) and for running the test suite.

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
ruff format --check .
mypy src
```

## License

MIT — see [LICENSE](LICENSE).
