# Sea Minerator guide

The details behind the [README](../README.md): what goes on each card, how
mining and importing behave, every setting, and how audio works.

- [Cards](#cards)
- [Mining](#mining)
- [Importing ready-made cards](#importing-ready-made-cards)
- [Settings](#settings)
- [Audio](#audio)

## Cards

Cards use their own note type, **Sea Minerator**, created automatically the
first time you mine or import:

- **Front:** the example sentence, with the mined expression highlighted in
  color. It plays the card's recording when it has one (the **Audio** field,
  filled by a recorded audio source), and otherwise speaks the sentence with
  Anki's `{{tts}}` tag.
- **Topic:** when the sentence exercises a grammar subject, a small badge
  above it names it, e.g. `Present perfect` or `Past simple · Verb to be`. A
  vocabulary-only sentence has no badge. The badge is the note's **Topic**
  field.
- **Back:** the highlighted expression as the sentence uses it, its
  translation in that same sentence (same subject and tense), and in
  parentheses its grammar class plus the grammar topics, e.g.
  `Have bought: comprei, já comprei (Verb · present-perfect)` for "I have
  bought a new car." The class always comes from a fixed list (`Noun`,
  `Verb`, `Phrasal verb`, `Idiom`, `Expression`…).
- **Tags:** only `anki-sea-minerator`, so mined cards can be told apart.

### Finding cards in the Browse window

- `topic:"Present perfect"` finds every card with that badge.
- `"back:*(Phrasal verb*"` finds every phrasal verb, since the class always
  comes from the same list.
- `tag:anki-sea-minerator` finds everything the add-on created.

### Older note types and the Topic field

A note type made by an older version has no Topic field. Adding one makes
the next sync a one-time full sync, so the first time a card would get a
badge, Sea Minerator asks first. If you decline, cards are created without
it; turn **Show the grammar subject as a badge** back on in the settings to
be asked again.

## Mining

`Tools → Mine vocabulary…` opens the wizard:

1. Paste your list and choose a deck, then click **Mine**.
2. Review each word's sentences and check the ones you want as cards. Each
   word shows its explanation and its grammar class, which you can change in
   the dropdown; each sentence shows its usage note and grammar topics.
3. Click **Create cards**. Anki creates them as one batch, undoable in one
   step (`Edit → Undo`).
4. The summary screen shows how many cards were created and any warnings
   (for example, a sentence where the expression text couldn't be located to
   highlight).

## Importing ready-made cards

`Tools → Import cards…` creates cards from text you already have, without
the AI. Paste one card per block: the front on one line, the back on the
next, and a blank line between cards:

```text
[Grammar] I've just arrived. I have just arrived.
Eu acabei de chegar.

[Grammar] Have you seen him?
Você viu ele?
```

Select part of a front or a back and press **Ctrl+B** (or click
**Highlight**) to color it like a mined expression; press it again on the
same text to remove the color. Pick a topic (e.g. `present perfect`) and a
deck, then **Create cards**.

- The back gets the topic in parentheses: `Eu acabei de chegar. (present-perfect)`.
- The topic also becomes the card's badge (`Present perfect`), which takes
  the place of a leading `[Grammar]` on the front. Any other leading `[Label]`
  is still shown on the card, and the audio reads only the sentence.
- Blocks without exactly two lines, and fronts that are only a `[Label]`, are
  skipped and listed.
- A card whose sentence already exists on a Sea Minerator card is rejected
  as a duplicate, whatever its label, since it would say the same thing.
- The whole import is one undo step (`Edit → Undo Import cards`).

## Settings

Open `Tools → Sea Minerator settings…` (or `Tools → Add-ons`, select
**Sea Minerator**, click **Config**).

### AI provider

- **Gemini**: free key from [Google AI Studio](https://aistudio.google.com/).
- **OpenAI & compatible**: an OpenAI key, or change the base URL to another
  compatible service (OpenRouter, Groq…) and use its key. The service and
  model must support `json_schema` structured outputs; some don't
  (DeepSeek's API, for instance, only offers plain JSON mode).
- **Anthropic**: a key from the [Anthropic Console](https://console.anthropic.com/).
- **Local**: run [Ollama](https://ollama.com/) or LM Studio; no key needed.
  The base URL defaults to Ollama (`http://localhost:11434/v1`); for LM
  Studio use `http://localhost:1234/v1`. Pick a model that supports
  structured output.

Paste the key, click **Load models**, choose a model, and **Test
connection**. Keys are stored in plain text in Anki's add-on folder.

### Everything else

- `native_language` — your language; explanations and translations of mined
  words are written in it. The mining screen asks for it the first time.
- `default_deck` — the deck pre-selected in the wizard.
- `tts_lang` — the language passed to Anki's `{{tts}}` tag, e.g. `en_US`.
  Changing it rewrites the note type's template, which affects existing cards.
- `tts_voices` and `tts_speed` — the voice and speaking speed. The dialog
  lists this computer's voices for the language, with **▶ Preview**; type a
  phone's voice after a comma so each device uses the first one it has.
  Voices other add-ons register, like AwesomeTTS's, are not supported: they
  need that add-on's own setup and don't exist on phones.
  Like `tts_lang`, they reach the note type the next time you create or
  import cards, and then apply to existing cards too.
- `highlight_color` — the CSS color used for the studied expression.
- `topic_badge` — **Show the grammar subject as a badge** (see
  [Cards](#cards)).
- `audio` — **Audio source**; see [Audio](#audio).

**Edit prompt…**, next to the native language, shows the prompt the model
receives for that language and lets you change it; **Reset to default** brings
back the built-in one. Brazilian Portuguese has a tuned prompt; the other
languages share a generic one. The response format and the grammar class and
topic rules are always added after your text, so an edit can't break them.

See [`src/seaminerator/config.md`](../src/seaminerator/config.md) for the
full reference.

## Audio

Each card's sentence is spoken in one of two ways, chosen with **Audio
source** in the settings:

- **System voice** (the default): nothing is recorded. The front uses
  Anki's `{{tts}}` tag, described below.
- **Recorded** (Google Translate or Gemini): when a card is created, its
  sentence is recorded to an MP3 stored in the collection's media and in the
  card's **Audio** field, so it sounds the same on every device, AnkiWeb
  included. With Gemini, a sentence Gemini can't record (or every sentence
  after Gemini stops, e.g. when its daily quota is reached) is recorded with
  Google Translate instead. If no source can record it (no network, the
  services are down), the card is still created and uses the system voice;
  the summary says which cards and why. Things to know:
  - Sentences are sent to the chosen service, and with Gemini to Google
    Translate for the ones Gemini can't record. Google Translate's endpoint
    is unofficial and may stop working; Gemini uses your Gemini API key, and
    its free tier allows about 100 sentences a day.
  - Gemini's default TTS model is `gemini-3.8-flash-lite-tts`; the older
    2.5 and 3.1 TTS models stop working on 2026-11-17.
  - Gemini audio is converted to MP3 with LAME, which Anki bundles on
    Windows and macOS. On Linux, install the `lame` package, or Gemini cards
    will use the system voice.
  - The first time you pick a recorded source, the settings add an Audio
    field to the note type: sync your other devices first, because the next
    sync will be a one-time full sync (choose Upload).
  - Undoing a batch removes its cards; their MP3 files stay in the media
    folder until **Tools → Check Media** removes them, as with any audio.

### What `{{tts}}` can and can't do

With the system voice, and for any card without a recording, the front
uses Anki's native `{{tts}}` tag, which asks whatever is running Anki to
speak the sentence using **the operating system's own text-to-speech
voices** at review time. That has real consequences worth knowing before
you rely on it:

- **Requires Anki 2.1.20+ on desktop**, AnkiDroid 2.17+, or AnkiMobile
  2.0.56+. Older clients will show the tag literally instead of speaking it.
- **No support on plain Linux.** Desktop TTS depends on the OS having a
  speech engine installed and configured (macOS and Windows ship one;
  Anki's `{{tts}}` support does not extend to typical bare Linux setups
  without extra configuration you'd have to do yourself).
- **Voice quality and availability depend on what's installed on each
  device.** The same card can sound different — or silent — on different
  computers or phones, because it's playing through whatever local voices
  exist there, not a bundled recording. Choosing voices in the settings
  pins them by name where they exist; a device without any of them still
  falls back to its first voice for the language.
- **Probably does not work on AnkiWeb.** AnkiWeb's browser-based reviewer
  does not reliably support `{{tts}}`; treat cards as desktop/mobile-app
  only if audio matters to you.

If your study setup depends on hearing every card reliably in the browser or
on Linux, choose a recorded audio source: recorded cards play everywhere,
and only cards whose recording failed depend on `{{tts}}`.
