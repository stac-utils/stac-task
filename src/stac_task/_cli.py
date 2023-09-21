import json
import sys
from pathlib import Path
from typing import Optional

import click

from . import _load, _registry
from ._payload import Payload


@click.group()
@click.option(
    "-f",
    "--file",
    help="A Python file to load as a module. Should include a top-level "
    "`stac_task.register_task()` call.",
)
@click.option(
    "-n",
    "--module-name",
    help=(
        "The module name to use for the file. If not "
        "provided, the file's stem will be used."
    ),
)
@click.option(
    "--load-plugins/--no-load-plugins",
    default=True,
    help="Whether to load any plugin modules",
    show_default=True,
)
def cli(
    file: Optional[str],
    module_name: Optional[str],
    load_plugins: bool,
) -> None:
    """Execute payloads, list tasks, or print their jsonschemas."""
    if file:
        file_as_path = Path(file)
        if not module_name:
            module_name = file_as_path.stem
        _load.file(file_as_path.absolute(), module_name)
    if load_plugins:
        _load.plugins()


@cli.command()
@click.argument("INPUT")
@click.argument("TASK", required=False)
@click.argument("OUTPUT", required=False)
def run(input: str, task: Optional[str], output: Optional[str]) -> None:
    """Executes a payload.

    If TASK is not provided, stac-task will match all registered tasks against
    the payload's task configurations. If there is one (and only one) match,
    that task will be executed. This makes it easy to run a task file:

        stac-task -f my_task.py run payload.json

    If OUTPUT is not provided, the output payload will be printed to standard
    output.
    """
    payload = Payload.from_href(input)
    if task is None:
        task_names = list(_registry.get_tasks().keys())
        matching_tasks = set(
            name for name in payload.process.tasks.keys() if name in task_names
        )
        if len(matching_tasks) == 1:
            task = matching_tasks.pop()
        elif len(matching_tasks) == 0:
            print(
                "ERROR: no task provided on the command line, and no registered tasks "
                "match the process tasks list",
                file=sys.stderr,
            )
            print(
                "Run `stac-task list` to see registered tasks",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            print(
                "ERROR: no task provided on the command line, and more than one "
                "registered tasks matches the process tasks list",
                file=sys.stderr,
            )
            print(
                f"Matching tasks: {', '.join(sorted(matching_tasks))}",
                file=sys.stderr,
            )
            sys.exit(1)
    result = payload.execute(task)
    if output is None:
        print(result.model_dump_json(indent=2))
    else:
        result.to_path(output)


@cli.command(name="list")
def list_command() -> None:
    """Lists all available tasks."""
    for key, value in _registry.get_tasks().items():  # type: ignore
        if value.__doc__:
            description = value.__doc__.split("\n")[0]
            print(f"{key}: {description}")
        else:
            print(key)


@cli.command()
@click.argument("TASK", required=False)
@click.argument("MODEL", required=False, default="input")
def jsonschema(task: Optional[str], model: str) -> None:
    """Returns the jsonschema for a task and its model.

    If TASK is not provided, and there is one (and only one) registered task,
    that task will be used. This makes it easy to print the jsonschema for a
    task defined and registered in a file:

        stac-task -f my_task.py jsonschema

    MODEL should be one of "input", "output", or "config". If it is not
    provided, it defaults to "input".
    """
    if not task:
        tasks = _registry.get_tasks()  # type: ignore
        if len(tasks) == 1:
            task = next(iter(tasks.keys()))
        else:
            print(
                "ERROR: TASK argument can only be omitted if there is one, and only "
                "one, registered task",
                file=sys.stderr,
            )
            sys.exit(1)
    task_class = _registry.get_task(task)  # type: ignore
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
