from __future__ import annotations

from pathlib import Path

from .tags import CLASS_TAGS

DEFAULT_PROMPT = """\
You are an English teacher specialized in linguistics and Anki flashcard creation.
You will receive a "list of the day" with English words or expressions.

For EACH item, produce data following these rules:
- Explanation: 2-3 lines, simple and direct meaning. State the grammatical class
  and one relevant rule/peculiarity (irregular verb + past, accompanying
  preposition, countable/uncountable). Base definitions on the Cambridge
  Dictionary (https://dictionary.cambridge.org/). Write the explanation in
  Portuguese.
- Translations: the most common Portuguese translations, based on Reverso Context
  (https://context.reverso.net/traducao/).
- Class tag and topics: follow the tagging rules given after these instructions.
- Sentences: exactly 5 natural English sentences, each 20 to 50 characters,
  authentic to everyday speech, drawing on Cambridge Dictionary, DK EFE
  (https://www.dkefe.com/en) and Reverso Context. For each sentence also give the
  exact substring to highlight (the studied expression as it literally appears in
  that sentence, including inflection) and a short English usage note.

Respond ONLY with JSON (no markdown fences) matching this schema:
{
  "words": [
    {
      "expression": "give up",
      "explanation": "...",
      "translations": ["Desistir", "Parar"],
      "class_tag": "phrasal-verb",
      "sentences": [
        {
          "text": "She has given up smoking.",
          "highlight": "given up",
          "note": "present perfect",
          "topics": ["present-perfect"]
        },
        {
          "text": "Never give up on dreams.",
          "highlight": "give up",
          "note": "imperative",
          "topics": []
        }
      ]
    }
  ]
}
"""


_TAGGING_RULES = """\
Tagging rules:
- Give every word exactly one "class_tag" from this list: {classes}.
- Classify by how the expression functions in your sentences. When it could be
  several classes, pick the one the sentences use.
- Multi-word phrases take the class of their head: noun phrase or compound
  noun -> noun; verb phrase or gerund phrase -> verb; adjective phrase ->
  adjective; adverbial phrase with a single adverbial function -> adverb.
- phrasal-verb: a verb plus particle(s), in any form, including the past
  participle ("take over", "locked down", "freaking out").
- idiom: a figurative meaning that cannot be deduced from the words
  ("wrap my head around", "sea legs", "go all out").
- expression: a fixed conversational chunk with a mostly literal meaning, a
  discourse marker, slang, or a fragment that fits no single class
  ("no wonder", "sort of", "thumbs up", "as far as I know").
- Give every sentence "topics": the grammar structures the highlighted
  expression itself carries in that sentence (its tense or form, e.g.
  present-perfect for "have been", verb-to-be, have-got, modals,
  conditionals). Ignore the tense of the other words in the sentence, and
  never tag themes, meanings or sentence types (questions, negation,
  exclamation, cause-and-effect). Use an empty list when the expression
  carries no grammar structure, which is the case for most nouns, adjectives,
  idioms and fixed expressions. A verb elsewhere in the sentence does not
  count: for "stepladder" in "The stepladder is in the garage.", topics is []
  (the "is" is not the studied expression). Never use a class tag as a topic.
- {existing}
- A topic names the structure family, never the specific word: modal-verbs
  (never modal-verb-will or modal-verb-would), conditionals (never
  second-conditional-would).
- Reuse an existing topic's exact spelling when the concept matches. Only when
  none fits, create a new topic tag in English kebab-case (e.g.
  past-continuous)."""


def tagging_instructions(topics: list[str]) -> str:
    if topics:
        existing = "Existing topic tags: " + ", ".join(topics) + "."
    else:
        existing = "There are no existing topic tags yet."
    return _TAGGING_RULES.format(classes=", ".join(CLASS_TAGS), existing=existing)


def load_prompt(path: str | None) -> str:
    if path:
        p = Path(path)
        if p.is_file():
            return p.read_text(encoding="utf-8")
    return DEFAULT_PROMPT
