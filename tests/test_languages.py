from seaminerator.core.languages import NATIVE_LANGUAGES


def test_there_are_twenty_languages():
    # A duplicated code would collapse into one dict entry and fail this.
    assert len(NATIVE_LANGUAGES) == 20


def test_each_language_is_keyed_by_its_own_code():
    for code, language in NATIVE_LANGUAGES.items():
        assert language.code == code


def test_brazilian_portuguese_comes_first():
    assert next(iter(NATIVE_LANGUAGES)) == "pt-BR"


def test_english_is_not_offered():
    assert not any(code.lower().startswith("en") for code in NATIVE_LANGUAGES)
    assert all(
        "English" not in language.english_name for language in NATIVE_LANGUAGES.values()
    )


def test_every_language_has_a_label_and_an_english_name():
    for language in NATIVE_LANGUAGES.values():
        assert language.label.strip()
        assert language.english_name.strip()
