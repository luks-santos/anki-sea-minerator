import minerator


def test_package_exposes_version():
    assert isinstance(minerator.__version__, str)
    assert minerator.__version__
