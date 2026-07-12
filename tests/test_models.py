import pytest

from minerator.models import (
    ImportedCard,
    Sentence,
    WordBlock,
    parse_imported_text,
    parse_mining_response,
)


def sample_payload():
    return {
        "words": [
            {
                "expression": "give up",
                "explanation": "To stop trying.",
                "translations": ["Desistir", "Parar"],
                "grammar_class": "Phrasal Verb",
                "sentences": [
                    {
                        "text": "Never give up.",
                        "highlight": "give up",
                        "note": "imperative",
                    },
                    {"text": "He gave up.", "highlight": "gave up"},
                ],
            }
        ]
    }


def test_parse_builds_word_blocks():
    words = parse_mining_response(sample_payload())
    assert len(words) == 1
    w = words[0]
    assert isinstance(w, WordBlock)
    assert w.expression == "give up"
    assert w.translations == ["Desistir", "Parar"]
    assert w.sentences[0] == Sentence(
        text="Never give up.", highlight="give up", note="imperative"
    )
    assert w.sentences[1].note == ""  # note defaults to empty


def test_parse_rejects_missing_words_key():
    with pytest.raises(ValueError):
        parse_mining_response({"nope": []})


def test_parse_imported_text_single_block_with_tag():
    cards, warnings = parse_imported_text(
        "[Grammar] We had a bad day.\nNós tivemos um dia ruim."
    )
    assert warnings == []
    assert cards == [
        ImportedCard(
            front="[Grammar] We had a bad day.", back="Nós tivemos um dia ruim."
        )
    ]


def test_parse_imported_text_single_block_without_tag():
    cards, warnings = parse_imported_text("Plain sentence.\nFrase simples.")
    assert warnings == []
    assert cards == [ImportedCard(front="Plain sentence.", back="Frase simples.")]


def test_parse_imported_text_multiple_blocks():
    text = (
        "[Grammar] We had a bad day.\n"
        "Nós tivemos um dia ruim.\n"
        "\n"
        "[Grammar] You did a great job.\n"
        "Você fez um ótimo trabalho."
    )
    cards, warnings = parse_imported_text(text)
    assert warnings == []
    assert len(cards) == 2
    assert cards[1].front == "[Grammar] You did a great job."
    assert cards[1].back == "Você fez um ótimo trabalho."


def test_parse_imported_text_tolerates_multiple_blank_lines_between_blocks():
    text = "Front one.\nBack one.\n\n\n\nFront two.\nBack two."
    cards, warnings = parse_imported_text(text)
    assert warnings == []
    assert len(cards) == 2


def test_parse_imported_text_skips_block_missing_back_line():
    text = "Front one.\nBack one.\n\nFront two only."
    cards, warnings = parse_imported_text(text)
    assert len(cards) == 1
    assert warnings == ["block 2 skipped: expected 2 lines (front, back), got 1"]


def test_parse_imported_text_skips_block_with_extra_lines():
    text = "Front.\nBack.\nExtra line."
    cards, warnings = parse_imported_text(text)
    assert cards == []
    assert warnings == ["block 1 skipped: expected 2 lines (front, back), got 3"]


def test_parse_imported_text_empty_input_returns_nothing():
    assert parse_imported_text("") == ([], [])
    assert parse_imported_text("   \n\n  ") == ([], [])
