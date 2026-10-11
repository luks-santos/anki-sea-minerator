import pytest

from seaminerator.core.config import Config
from seaminerator.core.languages import NATIVE_LANGUAGES
from seaminerator.core.prompt import (
    PROMPT_TEMPLATE,
    PT_BR_PROMPT,
    RESPONSE_FORMAT,
    default_prompt,
    prompt_for,
    tagging_instructions,
)
from seaminerator.core.tags import CLASS_TAGS


def test_brazilian_portuguese_has_a_dedicated_prompt():
    prompt = default_prompt("pt-BR")

    assert prompt == PT_BR_PROMPT
    assert "Portuguese" in prompt
    assert "Respond ONLY with JSON" not in prompt


def test_other_languages_fill_the_template_with_their_english_name():
    prompt = default_prompt("es")

    assert "Spanish" in prompt
    assert "Portuguese" not in prompt
    assert "{native_language}" not in prompt


def test_every_language_has_a_default_prompt_without_placeholders():
    for code in NATIVE_LANGUAGES:
        prompt = default_prompt(code)
        assert "{native_language}" not in prompt
        assert "Cambridge" in prompt


@pytest.mark.parametrize("code", ["", "xx", "en"])
def test_default_prompt_rejects_an_unchosen_or_unknown_language(code):
    with pytest.raises(KeyError):
        default_prompt(code)


def test_template_keeps_the_english_sources():
    assert "Cambridge" in PROMPT_TEMPLATE
    assert "Reverso" in PROMPT_TEMPLATE
    assert "Respond ONLY with JSON" not in PROMPT_TEMPLATE


def test_response_format_describes_every_field_without_a_portuguese_example():
    assert "Respond ONLY with JSON" in RESPONSE_FORMAT
    for name in ('"class_tag"', '"topics"', '"highlight"', '"translations"'):
        assert name in RESPONSE_FORMAT
    assert "grammar_class" not in RESPONSE_FORMAT
    assert "Desistir" not in RESPONSE_FORMAT


def test_prompt_for_prefers_the_users_edit():
    # Sent literally: no placeholder substitution in an edit.
    cfg = Config(native_language="es", prompts={"es": "Mi prompt {native_language} {}"})
    assert prompt_for(cfg) == "Mi prompt {native_language} {}"


def test_prompt_for_uses_the_default_without_an_edit():
    assert prompt_for(Config(native_language="pt-BR")) == PT_BR_PROMPT
    assert prompt_for(Config(native_language="es")) == default_prompt("es")


def test_prompt_for_ignores_edits_made_for_another_language():
    cfg = Config(native_language="es", prompts={"fr": "Mon prompt"})
    assert prompt_for(cfg) == default_prompt("es")


def test_prompt_for_requires_a_chosen_language():
    with pytest.raises(KeyError):
        prompt_for(Config())


def test_tagging_instructions_list_every_class():
    text = tagging_instructions([])
    for tag in CLASS_TAGS:
        assert tag in text


def test_tagging_instructions_list_every_existing_topic():
    text = tagging_instructions(["have-got", "past-simple"])
    assert "have-got, past-simple" in text
    assert "no existing topic tags" not in text


def test_tagging_instructions_handle_an_empty_topic_list():
    assert "There are no existing topic tags yet." in tagging_instructions([])


def test_tagging_instructions_include_the_classification_rules():
    text = tagging_instructions([])
    assert "phrasal-verb" in text
    assert "figurative" in text
    assert "kebab-case" in text


def test_tagging_instructions_tie_topics_to_the_highlighted_expression():
    text = tagging_instructions([])
    assert "expression itself carries in that sentence" in text
    assert "questions, negation" in text


def test_tagging_instructions_ask_for_one_topic_per_structure_family():
    text = tagging_instructions([])
    assert "modal-verbs" in text
    assert "modal-verb-will" in text


def test_tagging_instructions_leave_topics_empty_for_a_noun_next_to_a_verb():
    text = tagging_instructions([])
    assert "The stepladder is in the garage" in text
