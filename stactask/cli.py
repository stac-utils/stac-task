import argparse
import json
import logging
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any, cast

import fsspec

from stactask.task import Task


class DeprecatedStoreTrueAction(argparse._StoreTrueAction):
    def __call__(self, parser, namespace, values, option_string=None) -> None:  # type: ignore
        warnings.warn(f"Argument {self.option_strings} is deprecated.", stacklevel=2)
        super().__call__(parser, namespace, values, option_string)


class CLI:
    tasks: dict[str, Task]

    def __init__(self) -> None:
        self.tasks = {}

        self._build_argparser()

    def _build_argparser(self) -> None:
        self._parser = argparse.ArgumentParser(description="STAC Task management tools")
        self._parser.add_argument(
            "--version",
            help="Print version and exit",
            action="version",
            version="???",
        )
        self._parser.add_argument(
            "--logging",
            default="INFO",
            help="DEBUG, INFO, WARN, ERROR, CRITICAL",
        )
        self._parser.add_argument(
            "--output",
            default=None,
            help="Write output payload to this URL",
        )

        pparser = argparse.ArgumentParser(add_help=False)
        subparsers = self._parser.add_subparsers(dest="command")

        # run
        run_parser = subparsers.add_parser(
            "run",
            parents=[pparser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            help="Process STAC Item Collection",
        )
        run_parser.add_argument(
            "input",
            nargs="?",
            help="Full path of item collection to process (s3 or local)",
        )

        run_parser.add_argument(
            "--task",
            required=True,
            help="Name of the task you wish to run",
        )


        # additional options
        run_parser.add_argument(
            "--workdir",
            default=None,
            type=Path,
            help="Use this as work directory. Will be created.",
        )

        run_parser.add_argument(
            "--save-workdir",
            dest="save_workdir",
            action="store_true",
            default=False,
            help="Save workdir after completion",
        )

        # skips are deprecated in favor of boolean optionals
        run_parser.add_argument(
            "--skip-upload",
            dest="skip_upload",
            action=DeprecatedStoreTrueAction,
            default=False,
            help="DEPRECATED: Skip uploading of generated assets and STAC Items",
        )
        run_parser.add_argument(
            "--skip-validation",
            dest="skip_validation",
            action=DeprecatedStoreTrueAction,
            default=False,
            help="DEPRECATED: Skip validation of input payload",
        )

        run_parser.add_argument(
            "--upload",
            dest="upload",
            action="store_true",
            default=True,
            help="Upload generated assets and resulting STAC Items",
        )
        run_parser.add_argument(
            "--no-upload",
            dest="upload",
            action="store_false",
            help="Don't upload generated assets and resulting STAC Items",
        )
        run_parser.add_argument(
            "--validate",
            dest="validate",
            action="store_true",
            default=True,
            help="Validate input payload",
        )
        run_parser.add_argument(
            "--no-validate",
            dest="validate",
            action="store_false",
            help="Don't validate input payload",
        )

        run_parser.add_argument(
            "--local",
            action="store_true",
            default=False,
            help=""" Run local mode
(save-workdir = True, upload = False,
workdir = 'local-output', output = 'local-output/output-payload.json') """,
        )

        # metadata
        build_parser = subparsers.add_parser(
            "metadata",
            parents=[pparser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            help="Output metadata document for all registered STAC Tasks",
        )

        build_parser.add_argument(
            "--output",
            default=None,
            help="Write output task metadata to this URL",
        )

    def register_task(self, task: Task) -> None:
        self.tasks[task.name] = task

    def execute(self) -> None:
        args = self._parse_args(sys.argv[1:])
        cmd = args.pop("command")

        loglevel = args.pop("logging")
        logging.basicConfig(level=loglevel)

        href_out = args.pop("output", None)

        # quiet these loud loggers
        for ql in [
            "botocore",
            "s3transfer",
            "urllib3",
            "fsspec",
            "asyncio",
            "aiobotocore",
        ]:
            logging.getLogger(ql).propagate = False

        match cmd:
            case "run":
                output = self._run_task(args)
            case "metadata":
                output = self._task_metadata()

        self._write_output(output, href_out)

    def _parse_args(self, args: list[str]) -> dict[str, Any]:
        # turn Namespace into dictionary
        pargs = vars(self._parser.parse_args(args))
        # only keep keys that are not None
        pargs = {k: v for k, v in pargs.items() if v is not None}

        if pargs.pop("skip_validation", False):
            pargs["validate"] = False
        if pargs.pop("skip_upload", False):
            pargs["upload"] = False

        if pargs.pop("local", False):
            pargs["save_workdir"] = True
            pargs["upload"] = False
            if pargs.get("workdir") is None:
                pargs["workdir"] = "local-output"
            if pargs.get("output") is None:
                pargs["output"] = Path(pargs["workdir"]) / "output-payload.json"

        if pargs.get("command", None) is None:
            self._parser.print_help()
            sys.exit(0)

        return pargs

    def _task_metadata(self) -> dict[str, Any]:
        # create task metadata document
        from stactask import __version__

        metadata: dict[str, Any] = {
            "stactask_version": __version__,
            "tasks": {},
        }
        for name, task in self.tasks.items():
            metadata["tasks"][name] = task.metadata()

        return metadata

    def _run_task(self, args: dict[str, Any]) -> dict[str, Any]:
        href = args.pop("input", None)

        # read input
        if href is None:
            payload = json.load(sys.stdin)
        else:
            with fsspec.open(href) as f:
                payload = json.loads(f.read())

        # run task handler
        task_name = args.pop("task")
        payload_out = self.tasks[task_name].handler(payload, **args)

        return payload_out

    def _write_output(self, output: dict[str, Any], href_out: str | None = None) -> None:
        if href_out is None:
            json.dump(output, sys.stdout)
        else:
            with fsspec.open(href_out, "w") as f:
                f.write(json.dumps(output))
