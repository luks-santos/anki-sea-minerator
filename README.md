# anki-sea-minerator

A terminal application that automates mining English vocabulary into
[Anki](https://apps.ankiweb.net/) flashcards, powered by AI.

## The idea

Turn a daily list of English words/expressions into ready-to-study Anki cards,
without the manual copy-paste-and-record workflow.

You paste a "list of the day" in the terminal. An AI connector (Gemini first,
pluggable) returns structured data for each item — a short explanation, the
grammar class, translations, and example sentences. You pick which sentences
become cards. For each selected sentence the app builds an Anki note with the
mined expression highlighted in color and generates the audio (TTS), then inserts
it into a deck you choose — all through [AnkiConnect](https://ankiweb.net/shared/info/2055492159).

This replaces today's manual flow: prompting a chat LLM, copying sentences one by
one into Anki, and running AwesomeTTS by hand.

## How a card looks

- **Front:** the English sentence, with the mined expression highlighted in color,
  plus the generated audio.
  Example: `The <span style="color:#2563eb">presence of the press</span> is huge. [sound:…mp3]`
- **Back:** the expression, its translations, and grammar class.
  Example: `Presence of the press: Presença da imprensa, Presença da mídia (Noun phrase)`

## Planned workflow (`mine` command)

1. Health check — Anki open with AnkiConnect, and AI key configured.
2. Paste the list of the day in the terminal.
3. Pick the target deck for the session.
4. The AI returns structured results (explanation, translations, grammar class, sentences).
5. Review each word and select which sentences to turn into cards.
6. For each selected sentence: generate audio and create the Anki note.
7. See a summary of what was created.

## Key ideas

- **Terminal-first**, guided interactive flow.
- **Pluggable AI connector** — starts with Google Gemini.
- **Pluggable TTS engine** — defaults to `edge-tts`, with `gTTS` as an alternative.
- **Structured AI output (JSON)** — reliable parsing and exact highlighting, even
  with inflections (`give up → gave up → giving up`).
- **Reuses your existing Anki note type** with configurable field names.
- **Configurable, optimizable prompt** — the default preserves the pedagogical
  rules (Cambridge Dictionary, Reverso Context, DK EFE references).

## Planned tech stack

- **Python**
- **Typer** (CLI) + **Rich** (output) + **questionary** (interactive selection)
- **google-genai** (Gemini, structured JSON output)
- **edge-tts** / **gTTS** (text-to-speech)
- **httpx** (AnkiConnect HTTP API)

## Requirements (planned)

- Python 3.11+
- Anki desktop with the AnkiConnect add-on running
- A Google Gemini API key

## Install

```bash
pip install -e ".[dev]"
```

## Setup

1. Install the AnkiConnect add-on (code `2055492159`) and keep Anki open.
2. Get a free Gemini API key from Google AI Studio and export it:
   `export GEMINI_API_KEY=...` (or set it in the config file).

## Usage

```bash
minerator check          # verify Anki + API key
minerator config show    # inspect configuration
minerator mine           # interactive mining session
```
