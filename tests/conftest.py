import pytest
from anki.collection import Collection


@pytest.fixture
def col(tmp_path):
    collection = Collection(str(tmp_path / "test.anki2"))
    yield collection
    collection.close()
