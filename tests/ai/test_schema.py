from seaminerator.core.ai.schema import mining_schema, to_openai_strict
from seaminerator.core.tags import CLASS_TAGS


def word_schema(schema):
    return schema["properties"]["words"]["items"]


def sentence_schema(schema):
    return word_schema(schema)["properties"]["sentences"]["items"]


def test_mining_schema_uses_standard_lowercase_types():
    schema = mining_schema()
    assert schema["type"] == "object"
    assert schema["properties"]["words"]["type"] == "array"
    assert sentence_schema(schema)["properties"]["text"] == {"type": "string"}


def test_mining_schema_constrains_the_class_to_the_canonical_list():
    assert word_schema(mining_schema())["properties"]["class_tag"] == {
        "type": "string",
        "enum": list(CLASS_TAGS),
    }


def test_mining_schema_lists_properties_in_generation_order():
    schema = mining_schema()
    assert list(word_schema(schema)["properties"]) == [
        "expression",
        "explanation",
        "translations",
        "sentences",
        "class_tag",
    ]
    assert list(sentence_schema(schema)["properties"]) == [
        "text",
        "highlight",
        "note",
        "topics",
    ]


def test_mining_schema_leaves_the_note_optional():
    assert "note" not in sentence_schema(mining_schema())["required"]


def test_to_openai_strict_closes_and_requires_every_object():
    strict = to_openai_strict(mining_schema())
    for obj in (strict, word_schema(strict), sentence_schema(strict)):
        assert obj["additionalProperties"] is False
        assert obj["required"] == list(obj["properties"])


def test_to_openai_strict_does_not_mutate_its_input():
    schema = mining_schema()
    to_openai_strict(schema)
    assert "additionalProperties" not in schema
    assert "note" not in sentence_schema(schema)["required"]
