# AnkiWeb listing

Sea Minerator is add-on **1472156233** on AnkiWeb:
<https://ankiweb.net/shared/info/1472156233>. This page holds what goes into
its form, so every upload says the same thing.

## Releasing a new version

1. Bump the version in `pyproject.toml` and `human_version` in
   `src/seaminerator/manifest.json`, then build with `bash scripts/build.sh`.
2. Attach `dist/sea-minerator.ankiaddon` to a GitHub release.
3. On AnkiWeb, open **My Shared Items**, choose **Update** on Sea Minerator,
   upload the same file, and raise the branch's max version to the newest
   Anki release tested.

## Form fields

| Field | Value |
|---|---|
| Title | Sea Minerator: English sentence cards with AI (under 80 characters) |
| Tags | `english vocabulary sentences grammar ai gemini tts language-learning` |
| Support page | `https://github.com/luks-santos/anki-sea-minerator/issues` |
| Branch 1 | Supports `25.07` to `26.09.2`, matching `min_point_version` and `max_point_version` in `manifest.json` |
| File | `dist/sea-minerator.ankiaddon`, built with `bash scripts/build.sh` |

Leave the max version without a `-` prefix: with one, AnkiWeb would refuse
to serve the add-on to newer Anki releases.

AnkiWeb sets the add-on's update time and supported versions from this form,
not from `manifest.json`; the manifest's values apply to installs from a
file.

## Description

The description accepts Markdown and basic HTML. `<img>` keeps its `width`,
and the images come from this repository's `main` branch.

```markdown
**Turn the English words you pick up each day into Anki cards you'll remember.**

Paste your list of new words, an AI writes short example sentences for each one, you keep the ones you like, and each sentence becomes a card: the word highlighted, translated the way that sentence uses it, with audio and a badge naming its grammar.

<img src="https://raw.githubusercontent.com/luks-santos/anki-sea-minerator/main/docs/images/card-front.png" width="420" alt="Card front"> <img src="https://raw.githubusercontent.com/luks-santos/anki-sea-minerator/main/docs/images/card-back.png" width="420" alt="Card back">

Everyone learns English their own way. Sea Minerator is built around one of them: **learn each word inside a real sentence, hear it, and review it with spaced repetition.**

## Before you install

- **You need an AI provider.** A free Gemini key from Google AI Studio is the easiest start; OpenAI or a compatible service, Anthropic (Claude), or a local model with Ollama or LM Studio work too.
- **Your key is stored in plain text** in Anki's add-on folder, on your computer. It is sent only to the provider you chose.
- **Audio:** by default the cards speak with each device's own voice, so they can sound different, or stay silent, on another computer, on a phone or on AnkiWeb. For audio that plays everywhere, choose a recorded source (Google Translate or Gemini) in the settings.
- **You study English.** Explanations and translations come in your own language: 20 are available.
- Needs Anki 25.07 or later for desktop. The cards also work in AnkiDroid and AnkiMobile.

## How it works

1. **Tools → Mine vocabulary…**: paste one word or expression per line, choose a deck and click Mine.
2. Check the example sentences you want. Each word comes with a short explanation in your language, its translations and its grammar class.
3. Click **Create cards**: each sentence becomes one card, and the whole batch is one undo step.

<img src="https://raw.githubusercontent.com/luks-santos/anki-sea-minerator/main/docs/images/mine-review.png" width="640" alt="Choosing the sentences">

Already have your sentences? **Tools → Import cards…** turns them into the same kind of card without the AI: paste a front line and a back line for each card, and press Ctrl+B to highlight the part you're studying.

**Setup:** open **Tools → Sea Minerator settings…**, choose your native language and AI provider, paste the key, load the models and test the connection.

**Privacy:** the add-on has no server of its own. Your list of words goes to the AI provider you chose, with the grammar topics already in your collection; if you chose a recorded audio source, the sentences go to that service (Gemini falls back to Google Translate).

Guide, source code and bug reports: [github.com/luks-santos/anki-sea-minerator](https://github.com/luks-santos/anki-sea-minerator)
```
