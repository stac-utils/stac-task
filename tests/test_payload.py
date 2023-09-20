from pathlib import Path
from typing import Any, Callable, Dict, Optional

import pytest
from pydantic import BaseModel, ConfigDict
from stac_task import OneToOneTask, PassthroughTask, Payload, Process


class Input(BaseModel):
    pass


class Output(BaseModel):
    model_config = ConfigDict(extra="allow")

    the_meaning: int


class TheMeaning(OneToOneTask[Input, Output]):
    input = Input

    foo: Optional[bool] = None

    def process_one_to_one(self, item: Input) -> Output:
        fields: Dict[str, Any] = {"the_meaning": 42}
        if self.foo:
            fields["foo"] = "bar"
        return Output(**fields)


def test_from_path(data_path: Callable[[str], Path]) -> None:
    payload = Payload.from_href(str(data_path("sentinel2-l2a-j2k-payload.json")))
    assert len(payload.features) == 2


def test_from_path_indirect(data_path: Callable[[str], Path]) -> None:
    payload = Payload.from_href(str(data_path("indirect.json")))
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
    result = payload.execute("the-meaning", task_class=TheMeaning)
    assert result.features == [{"the_meaning": 42}]


def test_config() -> None:
    payload = Payload(
        features=[{}], process=Process(tasks={"the-meaning": {"foo": True}})
    )
    result = payload.execute("the-meaning", TheMeaning)
    assert result.features == [{"the_meaning": 42, "foo": "bar"}]
