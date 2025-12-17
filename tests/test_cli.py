import pytest

from stactask import CLI

from .tasks import NothingTask


@pytest.fixture
def cli() -> CLI:
    cli = CLI()
    cli.register_task(NothingTask)
    return cli


def test_parse_no_args(cli) -> None:
    with pytest.raises(SystemExit):
        cli._parse_args([])


def test_parse_args(cli) -> None:
    args = cli._parse_args(
        "run input --task nothing-task --save-workdir".split()
    )
    assert args["command"] == "run"
    assert args["logging"] == "INFO"
    assert args["input"] == "input"
    assert args["save_workdir"] is True
    assert args["upload"] is True
    assert args["validate"] is True


def test_parse_args_deprecated_skip(cli) -> None:
    args = cli._parse_args(
        "run input --task nothing-task --skip-upload --skip-validation".split()
    )
    assert args["upload"] is False
    assert args["validate"] is False


def test_parse_args_no_upload_and_no_validation(cli) -> None:
    args = cli._parse_args(
        "run input --task nothing-task --no-upload --no-validate".split()
    )
    assert args["upload"] is False
    assert args["validate"] is False


def test_parse_args_no_upload_and_validation(cli) -> None:
    args = cli._parse_args(
        "run input --task nothing-task --no-upload --validate".split()
    )
    assert args["upload"] is False
    assert args["validate"] is True


def test_parse_args_upload_and_no_validation(cli) -> None:
    args = cli._parse_args(
        "run input --task nothing-task --upload --no-validate".split()
    )
    assert args["upload"] is True
    assert args["validate"] is False


def test_parse_args_upload_and_validation(cli) -> None:
    args = cli._parse_args(
        "run input --task nothing-task --upload --validate".split()
    )
    assert args["upload"] is True
    assert args["validate"] is True
