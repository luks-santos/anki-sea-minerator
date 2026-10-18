# AnkiWeb listing

What goes into the form at <https://ankiweb.net/shared/addons/> (Upload)
for each release, so every upload says the same thing.

| Field | Value |
|---|---|
| Title | Sea Minerator: English sentence cards with AI |
| Tags | `english vocabulary sentences grammar ai gemini tts language-learning` |
| Support page | `https://github.com/luks-santos/anki-sea-minerator/issues` |
| Supported versions | 25.07 and later (matches `min_point_version` in `manifest.json`) |
| File | `dist/sea-minerator.ankiaddon`, built with `bash scripts/build.sh` |

AnkiWeb sets the add-on's update time and supported versions from this form,
not from `manifest.json`; the manifest's values apply to installs from a
file.

## Description

AnkiWeb accepts a limited set of HTML and turns each line break into a
break, so every list is on one line. The images come from this repository's
`main` branch. Check the page after saving: if a tag shows up as text,
replace it with plain text.

```html
<b>Turn the English words you pick up each day into Anki cards you'll remember.</b>

Paste your list of new words, an AI writes short example sentences for each one, you keep the ones you like, and each sentence becomes a card: the word highlighted, translated the way that sentence uses it, with audio and a badge naming its grammar.

<img src="https://raw.githubusercontent.com/luks-santos/anki-sea-minerator/main/docs/images/card-front.png" width="420" alt="Card front"> <img src="https://raw.githubusercontent.com/luks-santos/anki-sea-minerator/main/docs/images/card-back.png" width="420" alt="Card back">

Everyone learns English their own way. Sea Minerator is built around one of them: <b>learn each word inside a real sentence, hear it, and review it with spaced repetition.</b>

<b>Before you install</b>
<ul><li><b>You need an AI provider.</b> A free Gemini key from Google AI Studio is the easiest start; OpenAI or a compatible service, Anthropic (Claude), or a local model with Ollama or LM Studio work too.</li><li><b>Your key is stored in plain text</b> in Anki's add-on folder, on your computer.</li><li><b>Audio:</b> by default the cards speak with each device's own voice, so they can sound different, or stay silent, on another computer, on a phone or on AnkiWeb. For audio that plays everywhere, choose a recorded source (Google Translate or Gemini) in the settings.</li><li><b>You study English.</b> Explanations and translations come in your own language: 20 are available.</li><li>Needs Anki 25.07 or later for desktop. The cards also work in AnkiDroid and AnkiMobile.</li></ul>
<b>How it works</b>
<ol><li><b>Tools → Mine vocabulary…</b>: paste one word or expression per line, choose a deck and click Mine.</li><li>Check the example sentences you want. Each word comes with a short explanation in your language, its translations and its grammar class.</li><li>Click Create cards: each sentence becomes one card, and the whole batch is one undo step.</li></ol>
<img src="https://raw.githubusercontent.com/luks-santos/anki-sea-minerator/main/docs/images/mine-review.png" width="640" alt="Choosing the sentences">

Already have your sentences? <b>Tools → Import cards…</b> turns them into the same kind of card without the AI: paste a front line and a back line for each card, and press Ctrl+B to highlight the part you're studying.

<b>Setup:</b> open <b>Tools → Sea Minerator settings…</b>, choose your native language and AI provider, paste the key, load the models and test the connection.

<b>Privacy:</b> the add-on has no server of its own. Your list of words goes to the AI provider you chose, with the grammar topics already in your collection; if you chose a recorded audio source, the sentences go to that service (Gemini falls back to Google Translate).

Guide, source code and bug reports: <a href="https://github.com/luks-santos/anki-sea-minerator">github.com/luks-santos/anki-sea-minerator</a>
```
