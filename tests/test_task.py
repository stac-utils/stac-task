#!/usr/bin/env python
import json
from pathlib import Path

# import vcr
import pytest

from stactask import Task

testpath = Path(__file__).parent
cassettepath = testpath / "fixtures" / "cassettes"


from .tasks import DerivedItemTask, NothingTask


def get_test_items(name="sentinel2-l2a-j2k-items"):
    filename = testpath / "fixtures" / f"{name}.json"
    with open(filename) as f:
        items = json.loads(f.read())
    return items


def test_task_init():
    item_collection = get_test_items()
    t = NothingTask(item_collection)
    assert len(t._item_collection["features"]) == 1
    assert len(t.items) == 1
    assert t.logger.name == t.name
    assert t._save_workdir is False


def test_edit_items():
    items = get_test_items()
    t = NothingTask(items)
    t.process_definition["workflow"] = "test-task-workflow"
    assert t._item_collection["process"]["workflow"] == "test-task-workflow"


def test_edit_items2():
    items = get_test_items()
    t = NothingTask(items)
    assert t._item_collection["features"][0]["type"] == "Feature"


def test_tmp_workdir():
    t = NothingTask(get_test_items())
    assert t._save_workdir is False
    workdir = t._workdir
    assert workdir.parts[-1].startswith("tmp")
    assert workdir.is_dir() is True
    del t
    assert workdir.is_dir() is False


def test_workdir():
    t = NothingTask(get_test_items(), workdir=testpath / "test_task", save_workdir=True)
    assert t._save_workdir is True
    workdir = t._workdir
    assert workdir.parts[-1] == "test_task"
    assert workdir.is_dir() is True
    del t
    assert workdir.is_dir() is True
    workdir.rmdir()
    assert workdir.is_dir() is False


def test_parameters():
    items = get_test_items()
    t = NothingTask(items)
    assert t.process_definition["workflow"] == "cog-archive"
    assert (
        t.upload_options["path_template"]
        == items["process"]["upload_options"]["path_template"]
    )


def test_process():
    items = get_test_items()
    t = NothingTask(items)
    items = t.process()
    assert items[0]["type"] == "Feature"


def test_derived_item():
    t = DerivedItemTask(get_test_items())
    items = t.process(**t.parameters)
    links = [lk for lk in items[0]["links"] if lk["rel"] == "derived_from"]
    assert len(links) == 1
    self_link = [lk for lk in items[0]["links"] if lk["rel"] == "self"][0]
    assert links[0]["href"] == self_link["href"]


def test_task_handler():
    items = get_test_items()
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


if __name__ == "__main__":
    output = NothingTask.cli()
