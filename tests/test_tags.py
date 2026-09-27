from seaminerator.core.tags import (
    BASE_TOPICS,
    CLASS_TAGS,
    ORIGIN_TAG,
    RESERVED_TAGS,
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


def test_base_topics_are_kebab_case_and_not_classes():
    assert "modal-verbs" in BASE_TOPICS
    for topic in BASE_TOPICS:
        assert topic == normalize_tag(topic)
        assert topic not in CLASS_TAGS


def test_topic_vocabulary_of_empty_collection_is_the_base_topics():
    assert topic_vocabulary([]) == sorted(BASE_TOPICS)


def test_topic_vocabulary_adds_collection_topics_to_the_base():
    assert "used-to" in topic_vocabulary(["used-to"])


def test_topic_vocabulary_removes_classes_and_reserved():
    tags = ["noun", "anki-sea-minerator", "leech", "used-to"]
    vocabulary = topic_vocabulary(tags)
    assert "noun" not in vocabulary
    assert "anki-sea-minerator" not in vocabulary
    assert "leech" not in vocabulary


def test_topic_vocabulary_is_case_insensitive():
    vocabulary = topic_vocabulary(["Noun", "LEECH", "Marked"])
    assert vocabulary == sorted(BASE_TOPICS)


def test_topic_vocabulary_keeps_the_collection_spelling_of_a_base_topic():
    vocabulary = topic_vocabulary(["Past-Simple"])
    assert "Past-Simple" in vocabulary
    assert "past-simple" not in vocabulary


def test_class_label_is_readable():
    assert class_label("phrasal-verb") == "Phrasal verb"
    assert class_label("noun") == "Noun"
