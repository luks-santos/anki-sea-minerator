from __future__ import annotations

from ..tags import CLASS_TAGS


def mining_schema() -> dict:
    # Standard JSON Schema. Each `properties` dict is in generation order:
    # `class_tag` comes after `sentences` so the class is chosen once the
    # sentences exist, and `highlight` after `text`.
    string = {"type": "string"}
    string_list = {"type": "array", "items": {"type": "string"}}
    sentence = {
        "type": "object",
        "properties": {
            "text": dict(string),
            "highlight": dict(string),
            "note": dict(string),
            "topics": dict(string_list),
        },
        "required": ["text", "highlight", "topics"],
    }
    word = {
        "type": "object",
        "properties": {
            "expression": dict(string),
            "explanation": dict(string),
            "translations": dict(string_list),
            "sentences": {"type": "array", "items": sentence},
            "class_tag": {"type": "string", "enum": list(CLASS_TAGS)},
        },
        "required": [
            "expression",
            "explanation",
            "translations",
            "sentences",
            "class_tag",
        ],
    }
    return {
        "type": "object",
        "properties": {"words": {"type": "array", "items": word}},
        "required": ["words"],
    }


def to_openai_strict(schema: dict) -> dict:
    # OpenAI's strict structured outputs require every object to be closed
    # (`additionalProperties: false`) and every property to be required.
    result = dict(schema)
    if result.get("type") == "object":
        properties = {
            name: to_openai_strict(value)
            for name, value in result["properties"].items()
        }
        result["properties"] = properties
        result["required"] = list(properties)
        result["additionalProperties"] = False
    elif result.get("type") == "array":
        result["items"] = to_openai_strict(result["items"])
    return result
