from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pytest
from pydantic import BaseModel, ConfigDict
from stac_task import ExecutionError, Payload, Process, Task


class Input(BaseModel):
    pass


class Output(BaseModel):
    model_config = ConfigDict(extra="allow")

    the_meaning: int


class TheMeaning(Task[Input, Output]):
    input = Input

    foo: Optional[bool] = None

    def process(self, item: Input) -> List[Output]:
        fields: Dict[str, Any] = {"the_meaning": 42}
        if self.foo:
            fields["foo"] = "bar"
        return [Output(**fields)]


def test_from_path(data_path: Callable[[str], Path]) -> None:
    payload = Payload.from_href(str(data_path("sentinel2-l2a-j2k-payload.json")))
    assert len(payload.features) == 2


def test_from_path_indirect(data_path: Callable[[str], Path]) -> None:
    payload = Payload.from_href(str(data_path("indirect.json")))
    assert len(payload.features) == 2


def test_empty() -> None:
    with pytest.raises(ExecutionError):
        assert Payload().execute({}) == Payload()


def test_add_attribute() -> None:
    payload = Payload(features=[{}], process=Process(tasks={"the-meaning": {}}))
    result = payload.execute({"the-meaning": TheMeaning})
    assert result.features == [{"the_meaning": 42}]


def test_error_without_tasks() -> None:
    payload = Payload(features=[{}], process=Process(tasks={"the-meaning": {}}))
    with pytest.raises(ExecutionError):
        payload.execute({})


def test_config() -> None:
    payload = Payload(
        features=[{}], process=Process(tasks={"the-meaning": {"foo": True}})
    )
    result = payload.execute({"the-meaning": TheMeaning})
    assert result.features == [{"the_meaning": 42, "foo": "bar"}]
