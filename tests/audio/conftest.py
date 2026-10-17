import pytest

from seaminerator.core.audio import http


@pytest.fixture(autouse=True)
def sleeps(monkeypatch):
    """Every wait between retries, recorded instead of slept."""
    waited: list[float] = []
    monkeypatch.setattr(http, "_sleep", waited.append)
    return waited
