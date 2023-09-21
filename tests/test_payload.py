from pathlib import Path

import pytest
from stac_task import Payload, Process

from .test_task import PassthroughTask, TheMeaningTask


def test_from_path(data_path: Path) -> None:
    payload = Payload.from_href(str(data_path / "sentinel2-l2a-j2k-payload.json"))
    assert len(payload.features) == 2


def test_from_path_indirect(data_path: Path) -> None:
    payload = Payload.from_href(str(data_path / "indirect.json"))
    assert len(payload.features) == 2


def test_empty() -> None:
    with pytest.raises(ValueError):
        Payload().execute("not-a-task")


def test_no_config() -> None:
    with pytest.raises(ValueError):
        Payload().execute("passthrough-task", PassthroughTask)


def test_passthrough() -> None:
    payload = Payload(process=Process(tasks={"passthrough-task": {}}))
    output = payload.execute("passthrough-task", PassthroughTask)
    assert payload == output


def test_add_attribute() -> None:
    payload = Payload(features=[{}], process=Process(tasks={"the-meaning": {}}))
    result = payload.execute("the-meaning", task_class=TheMeaningTask)
    assert result.features == [{"the_meaning": 42}]


def test_config() -> None:
    payload = Payload(
        features=[{}], process=Process(tasks={"the-meaning": {"foo": True}})
    )
    result = payload.execute("the-meaning", TheMeaningTask)
    assert result.features == [{"the_meaning": 42, "foo": "bar"}]
