#!/usr/bin/env python
import json
from pathlib import Path
from typing import Any, Dict

import pytest

from stactask.exceptions import FailedValidation
from stactask.task import Task

from .tasks import DerivedItemTask, FailValidateTask, NothingTask

# import vcr


testpath = Path(__file__).parent
cassettepath = testpath / "fixtures" / "cassettes"


@pytest.fixture
def items() -> Dict[str, Any]:
    filename = testpath / "fixtures" / "sentinel2-l2a-j2k-payload.json"
    with open(filename) as f:
        items = json.loads(f.read())
    assert isinstance(items, dict)
    return items


@pytest.fixture
def nothing_task(items: Dict[str, Any]) -> Task:
    return NothingTask(items)


@pytest.fixture
def derived_item_task(items: Dict[str, Any]) -> Task:
    return DerivedItemTask(items)


def test_task_init(nothing_task: Task) -> None:
    assert len(nothing_task._payload["features"]) == 2
    assert len(nothing_task.items) == 2
    assert nothing_task.logger.name == nothing_task.name
    assert nothing_task._save_workdir is False


def test_failed_validation(items: Dict[str, Any]) -> None:
    with pytest.raises(FailedValidation):
        FailValidateTask(items)


def test_edit_items(nothing_task: Task) -> None:
    nothing_task.process_definition["workflow"] = "test-task-workflow"
    assert nothing_task._payload["process"]["workflow"] == "test-task-workflow"


def test_edit_items2(nothing_task: Task) -> None:
    assert nothing_task._payload["features"][0]["type"] == "Feature"


def test_tmp_workdir(items: Dict[str, Any]) -> None:
    nothing_task = NothingTask(items)
    assert nothing_task._save_workdir is False
    workdir = nothing_task._workdir
    assert workdir.parts[-1].startswith("tmp")
    assert workdir.is_dir() is True
    del nothing_task
    assert workdir.is_dir() is False


def test_workdir(items: Dict[str, Any]) -> None:
    t = NothingTask(items, workdir=testpath / "test_task", save_workdir=True)
    assert t._save_workdir is True
    workdir = t._workdir
    assert workdir.parts[-1] == "test_task"
    assert workdir.is_dir() is True
    del t
    assert workdir.is_dir() is True
    workdir.rmdir()
    assert workdir.is_dir() is False


def test_parameters(items: Dict[str, Any]) -> None:
    nothing_task = NothingTask(items)
    assert nothing_task.process_definition["workflow"] == "cog-archive"
    assert (
        nothing_task.upload_options["path_template"]
        == items["process"]["upload_options"]["path_template"]
    )


def test_process(nothing_task: Task) -> None:
    processed_items = nothing_task.process()
    assert processed_items[0]["type"] == "Feature"


def test_post_process(items: Dict[str, Any]) -> None:
    class PostProcessTask(NothingTask):
        name = "post-processing-test"
        version = "42"

        def post_process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
            item = super().post_process_item(item)
            item["properties"]["foo"] = "bar"
            return item

    payload = PostProcessTask.handler(items)
    for item in payload["features"]:
        assert item["properties"]["foo"] == "bar"
        assert item["properties"]["processing:software"]["post-processing-test"] == "42"


def test_derived_item(derived_item_task: Task) -> None:
    items = derived_item_task.process(**derived_item_task.parameters)
    links = [lk for lk in items[0]["links"] if lk["rel"] == "derived_from"]
    assert len(links) == 1
    self_link = [lk for lk in items[0]["links"] if lk["rel"] == "self"][0]
    assert links[0]["href"] == self_link["href"]


def test_task_handler(items: Dict[str, Any]) -> None:
    self_link = [lk for lk in items["features"][0]["links"] if lk["rel"] == "self"][0]
    output_items = DerivedItemTask.handler(items)
    derived_link = [
        lk for lk in output_items["features"][0]["links"] if lk["rel"] == "derived_from"
    ][0]
    assert derived_link["href"] == self_link["href"]
    assert (
        "derived-item-task"
        in output_items["features"][0]["properties"]["processing:software"]
    )


def test_parse_no_args() -> None:
    with pytest.raises(SystemExit):
        NothingTask.parse_args([])


def test_parse_args() -> None:
    args = NothingTask.parse_args("run input --save-workdir".split())
    assert args["command"] == "run"
    assert args["logging"] == "INFO"
    assert args["input"] == "input"
    assert args["save_workdir"] is True
    assert args["skip_upload"] is False
    assert args["skip_validation"] is False


if __name__ == "__main__":
    output = NothingTask.cli()
