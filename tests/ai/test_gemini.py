import json
from types import SimpleNamespace

from minerator.ai.gemini import GeminiConnector


class FakeModels:
    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=json.dumps(self._payload))


class FakeClient:
    def __init__(self, payload):
        self.models = FakeModels(payload)


def test_mine_parses_client_json_into_word_blocks():
    payload = {
        "words": [
            {
                "expression": "give up",
                "explanation": "stop trying",
                "translations": ["Desistir"],
                "grammar_class": "Phrasal Verb",
                "sentences": [{"text": "Never give up.", "highlight": "give up"}],
            }
        ]
    }
    fake = FakeClient(payload)
    connector = GeminiConnector(api_key="k", model="gemini-2.5-flash", client=fake)

    words = connector.mine(["give up"], prompt="RULES")

    assert words[0].expression == "give up"
    assert words[0].sentences[0].highlight == "give up"
    call = fake.models.calls[0]
    assert call["model"] == "gemini-2.5-flash"
    assert "give up" in call["contents"]
    assert "RULES" in call["contents"]
