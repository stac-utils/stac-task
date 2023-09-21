from pathlib import Path

import stac_task
from click.testing import CliRunner
from stac_task import _registry
from stac_task._cli import cli

from .test_task import PassthroughTask


def test_run_passthrough_no_output(data_path: Path) -> None:
    runner = CliRunner()
    with stac_task.register_task("passthrough", PassthroughTask):
        result = runner.invoke(
            cli,
            ["run", str(data_path / "passthrough.json"), "passthrough"],
        )
    assert result.exit_code == 0, result.stdout


def test_run_passthrough_no_task_name(data_path: Path) -> None:
    runner = CliRunner()
    with stac_task.register_task("passthrough", PassthroughTask):
        result = runner.invoke(cli, ["run", str(data_path / "passthrough.json")])
    assert result.exit_code == 0, result.stdout


def test_run_passthrough_no_task_name_no_tasks(data_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["run", str(data_path / "passthrough.json")])
    assert result.exit_code != 0


def test_run_passthrough_output(data_path: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    with stac_task.register_task("passthrough", PassthroughTask):
        result = runner.invoke(
            cli,
            [
                "run",
                str(data_path / "passthrough.json"),
                "passthrough",
                str(tmp_path / "item-collection.json"),
            ],
        )
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "item-collection.json").exists()


def test_run_passthrough_file(data_path: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    try:
        result = runner.invoke(
            cli,
            [
                "-f",
                str(data_path / "passthrough.py"),
                "run",
                str(data_path / "passthrough.json"),
            ],
        )
        assert result.exit_code == 0, result.stdout
    finally:
        _registry.unregister_task("passthrough")


def test_list() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0, result.stdout
