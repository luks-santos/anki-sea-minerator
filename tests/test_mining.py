import pytest

from seaminerator.core.ai.base import AIError, MiningRequest
from seaminerator.core.ai.schema import mining_schema
from seaminerator.core.mining import build_request, mine_words
from seaminerator.core.prompt import tagging_instructions

PAYLOAD = {
    "words": [
        {
            "expression": "give up",
            "explanation": "stop trying",
            "translations": ["Desistir"],
            "class_tag": "phrasal-verb",
            "sentences": [
                {"text": "It is.", "highlight": "is", "topics": ["verb-to-be"]}
            ],
        }
    ]
}


class FakeProvider:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def mine(self, request):
        self.requests.append(request)
        return self.response

    def list_models(self):
        return []


def test_build_request_assembles_prompt_rules_and_list():
    request = build_request(["give up", "whale"], "RULES", ["past-simple"])

    assert request == MiningRequest(
        text=(
            "RULES\n\n"
            + tagging_instructions(["past-simple"])
            + "\n\nList of the day:\ngive up\nwhale"
        ),
        schema=mining_schema(),
    )


def test_mine_words_parses_the_provider_json():
    provider = FakeProvider(PAYLOAD)

    blocks = mine_words(provider, ["give up"], "RULES", [])

    assert blocks[0].expression == "give up"
    assert blocks[0].class_tag == "phrasal-verb"
    assert provider.requests[0].text.startswith("RULES")


def test_mine_words_reuses_the_collection_spelling_of_topics():
    provider = FakeProvider(PAYLOAD)

    blocks = mine_words(provider, ["give up"], "RULES", ["Verb_To_Be"])

    assert blocks[0].sentences[0].topics == ["Verb_To_Be"]


def test_mine_words_turns_a_parse_error_into_an_ai_error():
    provider = FakeProvider({"words": [{"expression": None}]})

    with pytest.raises(AIError, match="outside the expected format"):
        mine_words(provider, ["give up"], "RULES", [])
