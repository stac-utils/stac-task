from pathlib import Path
from typing import Callable

import stac_task
from click.testing import CliRunner
from stac_task._cli import cli

from .test_task import PassthroughTask


def test_run_passthrough_no_output(data_path: Callable[[str], Path]) -> None:
    runner = CliRunner()
    with stac_task.register_task("passthrough", PassthroughTask):
        result = runner.invoke(
            cli,
            ["run", str(data_path("passthrough.json")), "passthrough"],
        )
    assert result.exit_code == 0, result.stdout


def test_run_passthrough_output(
    data_path: Callable[[str], Path], tmp_path: Path
) -> None:
    runner = CliRunner()
    with stac_task.register_task("passthrough", PassthroughTask):
        result = runner.invoke(
            cli,
            [
                "run",
                str(data_path("passthrough.json")),
                "passthrough",
                str(tmp_path / "item-collection.json"),
            ],
        )
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "item-collection.json").exists()
