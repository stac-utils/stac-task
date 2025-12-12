#!/usr/bin/env python
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import boto3
import pytest
from boto3utils import s3
from moto import mock_aws
from pystac import Asset

from stactask.exceptions import FailedValidation
from stactask.task import Task

from .tasks import DerivedItemTask, FailValidateTask, NothingTask

testpath = Path(__file__).parent
cassettepath = testpath / "fixtures" / "cassettes"


@pytest.fixture
def payload() -> dict[str, Any]:
    filename = testpath / "fixtures" / "sentinel2-l2a-j2k-payload.json"
    with filename.open() as f:
        payload = json.loads(f.read())
    assert isinstance(payload, dict)
    return payload


@pytest.fixture
def nothing_task(payload: dict[str, Any]) -> Task:
    return NothingTask(payload)


@pytest.fixture
def derived_item_task(payload: dict[str, Any]) -> Task:
    return DerivedItemTask(payload)


@pytest.fixture
def mock_s3_client() -> Callable[[], s3]:
    """Recreate the global S3 client within mock context to avoid state pollution.

    This fixture must be called from within a mock_aws context.
    """
    from boto3utils import s3

    from stactask import asset_io

    # This will be called during test execution, when mock is active
    def _recreate_client() -> s3:
        asset_io.global_s3_client = s3()
        return asset_io.global_s3_client

    return _recreate_client


def test_task_init(nothing_task: Task) -> None:
    assert len(nothing_task._payload["features"]) == 2
    assert len(nothing_task.items) == 2
    assert nothing_task.logger.name == nothing_task.name
    assert nothing_task._save_workdir is False


def test_failed_validation(payload: dict[str, Any]) -> None:
    with pytest.raises(FailedValidation, match="Extra context"):
        FailValidateTask(payload)


def test_deprecated_payload_dict(nothing_task: Task) -> None:
    nothing_task._payload["process"] = nothing_task._payload["process"][0]
    with pytest.warns(DeprecationWarning):
        _ = nothing_task.process_definition


def test_workflow_options_append_task_options(nothing_task: Task) -> None:
    nothing_task._payload["process"][0]["workflow_options"] = {
        "workflow_option": "workflow_option_value",
    }
    parameters = nothing_task.parameters
    assert parameters == {
        "do_nothing": True,
        "workflow_option": "workflow_option_value",
    }


def test_workflow_options_populate_when_no_task_options(nothing_task: Task) -> None:
    nothing_task._payload["process"][0]["tasks"].pop("nothing-task")
    nothing_task._payload["process"][0]["workflow_options"] = {
        "workflow_option": "workflow_option_value",
    }
    parameters = nothing_task.parameters
    assert parameters == {
        "workflow_option": "workflow_option_value",
    }


def test_task_options_supersede_workflow_options(nothing_task: Task) -> None:
    nothing_task._payload["process"][0]["workflow_options"] = {
        "do_nothing": False,
        "workflow_option": "workflow_option_value",
    }
    parameters = nothing_task.parameters
    assert parameters == {
        "do_nothing": True,
        "workflow_option": "workflow_option_value",
    }


def test_edit_items(nothing_task: Task) -> None:
    nothing_task.process_definition["workflow"] = "test-task-workflow"
    assert nothing_task._payload["process"][0]["workflow"] == "test-task-workflow"


def test_edit_items2(nothing_task: Task) -> None:
    assert nothing_task._payload["features"][0]["type"] == "Feature"


@pytest.mark.parametrize("save_workdir", [False, True, None])
def test_tmp_workdir(payload: dict[str, Any], save_workdir: bool | None) -> None:
    t = NothingTask(payload, save_workdir=save_workdir)
    expected = save_workdir if save_workdir is not None else False
    assert t._save_workdir is expected
    workdir = t._workdir
    assert workdir.parts[-1].startswith("tmp")
    assert workdir.is_absolute() is True
    assert workdir.is_dir() is True
    t.cleanup_workdir()
    assert workdir.exists() is expected


@pytest.mark.parametrize("save_workdir", [False, True, None])
def test_workdir(
    payload: dict[str, Any],
    tmp_path: Path,
    save_workdir: bool | None,
) -> None:
    t = NothingTask(payload, workdir=tmp_path / "test_task", save_workdir=save_workdir)
    expected = save_workdir if save_workdir is not None else True
    assert t._save_workdir is expected
    workdir = t._workdir
    assert workdir.parts[-1] == "test_task"
    assert workdir.is_absolute() is True
    assert workdir.is_dir() is True
    t.cleanup_workdir()
    assert workdir.exists() is expected


def test_parameters(payload: dict[str, Any]) -> None:
    nothing_task = NothingTask(payload)
    assert nothing_task.process_definition["workflow"] == "cog-archive"
    assert (
        nothing_task.upload_options["path_template"]
        == payload["process"][0]["upload_options"]["path_template"]
    )


def test_process(nothing_task: Task) -> None:
    processed_items = nothing_task.process()
    assert processed_items[0]["type"] == "Feature"


def test_post_process(payload: dict[str, Any]) -> None:
    class PostProcessTask(NothingTask):
        name = "post-processing-test"
        version = "42"

        def post_process_item(self, item: dict[str, Any]) -> dict[str, Any]:
            item["properties"]["foo"] = "bar"
            item["stac_extensions"].insert(0, "zzz")
            return super().post_process_item(item)

    payload_out = PostProcessTask.handler(payload)
    for item in payload_out["features"]:
        assert item["properties"]["foo"] == "bar"
        stac_extensions = item["stac_extensions"]
        assert item["stac_extensions"] == sorted(stac_extensions)


def test_derived_item(derived_item_task: Task) -> None:
    items = derived_item_task.process(**derived_item_task.parameters)
    links = [lk for lk in items[0]["links"] if lk["rel"] == "derived_from"]
    assert len(links) == 1
    self_link = next(lk for lk in items[0]["links"] if lk["rel"] == "self")
    assert links[0]["href"] == self_link["href"]


def test_task_handler(payload: dict[str, Any]) -> None:
    self_link = next(
        lk for lk in payload["features"][0]["links"] if lk["rel"] == "self"
    )
    output_items = DerivedItemTask.handler(payload)
    derived_link = next(
        lk for lk in output_items["features"][0]["links"] if lk["rel"] == "derived_from"
    )
    assert derived_link["href"] == self_link["href"]


def test_parse_no_args() -> None:
    with pytest.raises(SystemExit):
        NothingTask.parse_args([])


def test_parse_args() -> None:
    args = NothingTask.parse_args("run input --save-workdir".split())
    assert args["command"] == "run"
    assert args["logging"] == "INFO"
    assert args["input"] == "input"
    assert args["save_workdir"] is True
    assert args["upload"] is True
    assert args["validate"] is True


def test_parse_args_deprecated_skip() -> None:
    args = NothingTask.parse_args("run input --skip-upload --skip-validation".split())
    assert args["upload"] is False
    assert args["validate"] is False


def test_parse_args_no_upload_and_no_validation() -> None:
    args = NothingTask.parse_args("run input --no-upload --no-validate".split())
    assert args["upload"] is False
    assert args["validate"] is False


def test_parse_args_no_upload_and_validation() -> None:
    args = NothingTask.parse_args("run input --no-upload --validate".split())
    assert args["upload"] is False
    assert args["validate"] is True


def test_parse_args_upload_and_no_validation() -> None:
    args = NothingTask.parse_args("run input --upload --no-validate".split())
    assert args["upload"] is True
    assert args["validate"] is False


def test_parse_args_upload_and_validation() -> None:
    args = NothingTask.parse_args("run input --upload --validate".split())
    assert args["upload"] is True
    assert args["validate"] is True


def test_collection_mapping(nothing_task: Task) -> None:
    assert nothing_task.collection_mapping == {
        "sentinel-2-l2a": "$[?(@.id =~ 'S2[AB].*')]",
    }


@mock_aws
def test_s3_upload(nothing_task: Task, mock_s3_client: Callable[[], s3]) -> None:
    # start S3 mocks
    s3_client = boto3.client("s3")
    s3_client.create_bucket(
        Bucket="sentinel-cogs",
        CreateBucketConfiguration={
            "LocationConstraint": "us-west-2",
        },
    )
    # Recreate global s3 client within mock context
    mock_s3_client()
    # end S3 mocks

    item = nothing_task.items.items[0]
    key1_path = nothing_task._workdir / "foo.txt"
    key1_path.write_text("some text")
    asset = Asset(href=str(key1_path))
    item.add_asset("key1", asset)
    item_after_upload = nothing_task.upload_local_item_assets_to_s3(item)

    assert (
        item_after_upload.assets["key1"].href
        == "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-2-l2a/52/H/GH/2022/10/S2A_52HGH_20221007_0_L2A/foo.txt"
    )


if __name__ == "__main__":
    output = NothingTask.cli()
