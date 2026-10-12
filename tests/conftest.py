import pytest

from atlas.store import Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "test.db")
