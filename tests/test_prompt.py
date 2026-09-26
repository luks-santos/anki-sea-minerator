from seaminerator.core.prompt import DEFAULT_PROMPT, load_prompt, tagging_instructions
from seaminerator.core.tags import CLASS_TAGS


def test_default_prompt_mentions_json_and_rules():
    assert "JSON" in DEFAULT_PROMPT
    assert "highlight" in DEFAULT_PROMPT
    assert "Cambridge" in DEFAULT_PROMPT
    assert "Reverso" in DEFAULT_PROMPT


def test_load_prompt_returns_default_when_no_path():
    assert load_prompt(None) == DEFAULT_PROMPT
    assert load_prompt("") == DEFAULT_PROMPT


def test_load_prompt_reads_file(tmp_path):
    f = tmp_path / "custom.txt"
    f.write_text("my custom prompt", encoding="utf-8")
    assert load_prompt(str(f)) == "my custom prompt"


def test_load_prompt_falls_back_when_missing(tmp_path):
    missing = tmp_path / "nope.txt"
    assert load_prompt(str(missing)) == DEFAULT_PROMPT


def test_default_prompt_describes_class_tag_and_topics():
    assert '"class_tag"' in DEFAULT_PROMPT
    assert '"topics"' in DEFAULT_PROMPT
    assert "grammar_class" not in DEFAULT_PROMPT


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
