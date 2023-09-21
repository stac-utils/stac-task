from pathlib import Path

import pytest
from pystac import Item


@pytest.fixture
def data_path() -> Path:
    return Path(__file__).parent / "data"


@pytest.fixture
def item(data_path: Path) -> Item:
    return Item.from_file(str(data_path / "simple-item.json"))
