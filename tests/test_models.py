import pytest

from minerator.models import Sentence, WordBlock, parse_mining_response


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
