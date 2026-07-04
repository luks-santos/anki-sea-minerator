from minerator.prompt import DEFAULT_PROMPT, load_prompt


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
