import seaminerator


def test_package_imports_without_anki_installed():
    assert seaminerator.mw is None
