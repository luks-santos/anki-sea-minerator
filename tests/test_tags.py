from seaminerator.core.tags import (
    CLASS_TAGS,
    ORIGIN_TAG,
    RESERVED_TAGS,
    card_tags,
    class_label,
    normalize_tag,
    topic_vocabulary,
)


def test_class_tags_are_the_canonical_list_in_order():
    assert CLASS_TAGS == (
        "noun",
        "verb",
        "adjective",
        "adverb",
        "pronoun",
        "determiner",
        "preposition",
        "conjunction",
        "interjection",
        "phrasal-verb",
        "idiom",
        "expression",
    )


def test_reserved_tags_include_origin_leech_and_marked():
    assert RESERVED_TAGS == frozenset({"anki-sea-minerator", "leech", "marked"})
    assert ORIGIN_TAG == "anki-sea-minerator"


def test_normalize_tag_lowercases_and_hyphenates_spaces_and_underscores():
    assert normalize_tag("Present Perfect") == "present-perfect"
    assert normalize_tag("  Past_Simple  ") == "past-simple"


def test_normalize_tag_folds_accents_to_ascii():
    assert normalize_tag("gíria") == "giria"
    assert normalize_tag("Expressão Verbal") == "expressao-verbal"


def test_normalize_tag_drops_punctuation_and_collapses_hyphens():
    assert normalize_tag("noun (informal)") == "noun-informal"
    assert normalize_tag("verb / adjective") == "verb-adjective"
    assert normalize_tag("--phrasal--verb--") == "phrasal-verb"


def test_normalize_tag_keeps_hierarchy_separator():
    assert normalize_tag("Grammar::Past Simple") == "grammar::past-simple"


def test_normalize_tag_can_return_empty():
    assert normalize_tag("") == ""
    assert normalize_tag("  !!! ") == ""


def test_topic_vocabulary_removes_classes_and_reserved_and_sorts():
    tags = ["verb-to-be", "noun", "anki-sea-minerator", "past-simple", "leech"]
    assert topic_vocabulary(tags) == ["past-simple", "verb-to-be"]


def test_topic_vocabulary_is_case_insensitive():
    tags = ["Noun", "LEECH", "Marked", "have-got"]
    assert topic_vocabulary(tags) == ["have-got"]


def test_topic_vocabulary_of_empty_collection_is_empty():
    assert topic_vocabulary([]) == []


def test_class_label_is_readable():
    assert class_label("phrasal-verb") == "Phrasal verb"
    assert class_label("noun") == "Noun"


def test_card_tags_puts_origin_then_class_then_topics():
    assert card_tags("verb", ["past-simple", "verb-to-be"]) == [
        "anki-sea-minerator",
        "verb",
        "past-simple",
        "verb-to-be",
    ]


def test_card_tags_removes_duplicates_empty_and_reserved_topics():
    tags = card_tags("verb", ["verb", "past-simple", "", "past-simple", "leech"])
    assert tags == ["anki-sea-minerator", "verb", "past-simple"]


def test_card_tags_with_no_topics():
    assert card_tags("noun", []) == ["anki-sea-minerator", "noun"]
