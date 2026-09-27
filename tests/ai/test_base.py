import pytest

from seaminerator.core.ai.base import (
    OUTSIDE_FORMAT_MESSAGE,
    AIError,
    parse_json_object,
)


def test_parse_json_object_reads_an_object():
    assert parse_json_object('{"words": []}') == {"words": []}


def test_parse_json_object_strips_a_markdown_fence():
    text = '```json\n{"words": []}\n```'
    assert parse_json_object(text) == {"words": []}


def test_parse_json_object_strips_an_uppercase_fence():
    assert parse_json_object('```JSON\n{"words": []}\n```') == {"words": []}


def test_parse_json_object_finds_a_fence_after_some_text():
    text = 'Here it is:\n```json\n{"words": []}\n```\nEnjoy!'
    assert parse_json_object(text) == {"words": []}


def test_parse_json_object_rejects_text_that_is_not_json():
    with pytest.raises(AIError, match="outside the expected format"):
        parse_json_object("sorry, I can't help")


def test_parse_json_object_rejects_json_that_is_not_an_object():
    with pytest.raises(AIError) as info:
        parse_json_object("[1, 2]")
    assert str(info.value) == OUTSIDE_FORMAT_MESSAGE
