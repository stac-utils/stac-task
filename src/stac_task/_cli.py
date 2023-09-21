import json
import sys
from pathlib import Path
from typing import Optional

import click

import stac_task
from stac_task import Payload


@click.group()
@click.option(
    "-f",
    "--file",
    help="A Python file to load as a module, hopefully with a top-level "
    "`stac_task.register_task()` call.",
)
@click.option(
    "--load-plugins/--no-load-plugins",
    default=True,
    help="Whether to load any plugin modules",
)
def cli(file: Optional[str], load_plugins: bool) -> None:
    """Runs stac-task commands."""
    if file:
        stac_task.load_file(Path(file).absolute())
    if load_plugins:
        stac_task.load_plugins()


@cli.command()
@click.argument("INPUT")
@click.argument("TASK")
@click.argument("OUTPUT", required=False)
def run(input: str, task: str, output: Optional[str]) -> None:
    """Runs a payload."""
    payload = Payload.from_href(input)
    result = payload.execute(task)
    if output is None:
        print(result.model_dump_json(indent=2))
    else:
        result.to_path(output)


@cli.command()
def list() -> None:
    """Lists all available tasks."""
    for key, value in stac_task.get_tasks().items():  # type: ignore
        if value.__doc__:
            description = value.__doc__.split("\n")[0]
            print(f"{key}: {description}")
        else:
            print(key)


@cli.command()
@click.argument("TASK")
@click.argument("MODEL")
def jsonschema(task: str, model: str) -> None:
    """Returns the jsonschema for a task and its model.

    MODEL should be one of "input", "output", or "config".
    """
    tasks = stac_task.get_tasks()  # type: ignore
    if task not in tasks:
        print(f"Invalid task: {task}", file=sys.stderr)
        print("Run `stac-task --list` to see available tasks", file=sys.stderr)
        sys.exit(1)
    task_class = tasks[task]
    if model.lower() == "input":
        output = task_class.input.model_json_schema()
    elif model.lower() == "output":
        output = task_class.output.model_json_schema()
    elif model.lower() == "config":
        output = task_class.model_json_schema()
    else:
        print(f"Invalid model: {model}", file=sys.stderr)
        print("Must be one of 'input', 'output', or 'config'", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(output, indent=2))
