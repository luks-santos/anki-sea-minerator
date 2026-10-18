from __future__ import annotations

from .config import Config
from .languages import NATIVE_LANGUAGES
from .tags import CLASS_TAGS

# The prompt's body: the only part a user can edit. The response format and
# the tagging rules are appended by build_request, so no edit can break them.
PT_BR_PROMPT = """\
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
- Translate verb tenses by meaning, not by form. Portuguese "ter + particípio"
  (tenho visto, tem feito) means an action repeated or still going on up to
  now, so it rarely matches the English present perfect. Use the pretérito
  perfeito for a finished action or a life experience ("I have seen that
  movie" -> vi, já vi; "I haven't called her" -> não liguei, ainda não
  liguei), the presente for a state that still holds ("I have known him for
  years" -> conheço há anos), and "ter + particípio" only when the sentence
  says the action keeps repeating up to now ("She has called a lot lately" ->
  tem ligado muito).
- Class tag and topics: follow the tagging rules given after these instructions.
- Sentences: exactly 5 natural English sentences, each 20 to 50 characters,
  authentic to everyday speech, drawing on Cambridge Dictionary, DK EFE
  (https://www.dkefe.com/en) and Reverso Context. For each sentence also give the
  exact substring to highlight (the studied expression as it literally appears in
  that sentence, including inflection), its Portuguese translation as that
  sentence uses it, and a short English usage note.
"""

# For languages without a dedicated prompt. Cambridge stays the definition
# source (the studied language is always English); Reverso is only an example
# because it doesn't cover every language.
PROMPT_TEMPLATE = """\
You are an English teacher specialized in linguistics and Anki flashcard creation.
You will receive a "list of the day" with English words or expressions.

For EACH item, produce data following these rules:
- Explanation: 2-3 lines, simple and direct meaning. State the grammatical class
  and one relevant rule/peculiarity (irregular verb + past, accompanying
  preposition, countable/uncountable). Base definitions on the Cambridge
  Dictionary (https://dictionary.cambridge.org/). Write the explanation in
  {native_language}.
- Translations: the most common {native_language} translations, based on
  bilingual dictionaries and parallel-text resources such as Reverso Context
  (https://context.reverso.net/).
- Class tag and topics: follow the tagging rules given after these instructions.
- Sentences: exactly 5 natural English sentences, each 20 to 50 characters,
  authentic to everyday speech, drawing on Cambridge Dictionary, DK EFE
  (https://www.dkefe.com/en) and Reverso Context. For each sentence also give the
  exact substring to highlight (the studied expression as it literally appears in
  that sentence, including inflection), its {native_language} translation as
  that sentence uses it, and a short English usage note.
"""

DEDICATED_PROMPTS: dict[str, str] = {"pt-BR": PT_BR_PROMPT}

# Every provider enforces the JSON schema through its API; the example only
# guides quality. Explanation and translations are left as "..." so the
# example carries no language into the others.
RESPONSE_FORMAT = """\
Each sentence's "translation" translates its highlight as used in that
sentence: same subject, tense and number.

Respond ONLY with JSON (no markdown fences) matching this schema:
{
  "words": [
    {
      "expression": "give up",
      "explanation": "...",
      "translations": ["...", "..."],
      "class_tag": "phrasal-verb",
      "sentences": [
        {
          "text": "She has given up smoking.",
          "highlight": "given up",
          "translation": "...",
          "note": "present perfect",
          "topics": ["present-perfect"]
        },
        {
          "text": "Never give up on dreams.",
          "highlight": "give up",
          "translation": "...",
          "note": "imperative",
          "topics": []
        }
      ]
    }
  ]
}"""


def default_prompt(code: str) -> str:
    # KeyError for "" or an unknown code: callers check that a language is
    # chosen, and silently picking one would mine in the wrong language.
    language = NATIVE_LANGUAGES[code]
    if code in DEDICATED_PROMPTS:
        return DEDICATED_PROMPTS[code]
    # replace, not format: any other brace in the text stays inert.
    return PROMPT_TEMPLATE.replace("{native_language}", language.english_name)


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


def prompt_for(cfg: Config) -> str:
    # An edit belongs to its language only: switching languages never sends
    # another language's prompt.
    return cfg.prompts.get(cfg.native_language) or default_prompt(cfg.native_language)
