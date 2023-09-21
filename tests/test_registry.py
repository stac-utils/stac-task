import pytest
import stac_task

from .test_task import PassthroughTask


def test_context_manager() -> None:
    with pytest.raises(ValueError):
        stac_task.get_task("passthrough")
    with stac_task.register_task("passthrough", PassthroughTask):
        stac_task.get_task("passthrough")
    with pytest.raises(ValueError):
        stac_task.get_task("passthrough")
