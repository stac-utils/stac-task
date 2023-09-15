from pathlib import Path
from typing import Callable

import pytest


@pytest.fixture
def data_path() -> Callable[[str], Path]:
    def f(file_name: str) -> Path:
        return Path(__file__).parent / "data" / file_name

    return f
