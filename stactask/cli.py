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
        self._parser = argparse.ArgumentParser(description="?!?!?!?!")
        self._parser.add_argument(
            "--version",
            help="Print version and exit",
            action="version",
            version="???",
        )
        pparser = argparse.ArgumentParser(add_help=False)
        self._parser.add_argument(
            "--logging",
            default="INFO",
            help="DEBUG, INFO, WARN, ERROR, CRITICAL",
        )

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

        run_parser.add_argument(
            "--output",
            default=None,
            help="Write output payload to this URL",
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

        # build
        build_parser = subparsers.add_parser(
            "build",
            parents=[pparser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            help="Build all STAC Tasks",
        )

        build_parser.add_argument(
            "--image-tag",
            required=True,
            help="URI to push docker image to",
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
                self._run_task(args)
            case "build":
                self._build_tasks(args)

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

    def _build_tasks(self, args: dict[str, Any]) -> None:
        # create task metadata document
        from stactask import __version__

        metadata: dict[str, Any] = {
            "stactask_version": __version__,
            "tasks": {},
        }
        for name, task in self.tasks.items():
            input_schema = output_schema = None
            if task.input_model:
                input_schema = task.input_model.model_json_schema()
            if task.output_model:
                output_schema = task.output_model.model_json_schema()

            task_metadata = {
                "name": name,
                "version": task.version,
                "description": task.description,
                "input_schema": input_schema,
                "output_schema": output_schema,
            }
            metadata["tasks"][name] = task_metadata

        # build docker image
        subprocess.check_call(  # noqa: S603
            [  # noqa: S607
                "docker",
                "buildx",
                "build",
                "-t",
                args["image_tag"],
                "--label",
                f"stactask_metadata={json.dumps(metadata)}",
                "-f",
                "Dockerfile",
                ".",
            ],
        )

        # push docker image
        def _push_image(image_tag: str) -> None:
            # noop, replace later
            return None

        image_tag = args["image_tag"]
        cast(str, image_tag)
        _push_image(args["image_tag"])

    def _run_task(self, args: dict[str, Any]) -> None:
        href = args.pop("input", None)
        href_out = args.pop("output", None)

        # read input
        if href is None:
            payload = json.load(sys.stdin)
        else:
            with fsspec.open(href) as f:
                payload = json.loads(f.read())

        # run task handler
        task_name = args.pop("task")
        payload_out = self.tasks[task_name].handler(payload, **args)

        # write output
        if href_out is None:
            json.dump(payload_out, sys.stdout)
        else:
            with fsspec.open(href_out, "w") as f:
                f.write(json.dumps(payload_out))
