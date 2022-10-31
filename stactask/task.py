import argparse
import asyncio
import itertools
import json
import logging
import sys
import warnings
from abc import ABC, abstractmethod
from copy import deepcopy
from os import makedirs
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Dict, List, Optional, Union

import fsspec
from pystac import ItemCollection

from .asset_io import (
    download_item_assets,
    download_items_assets,
    upload_item_assets_to_s3,
)
from .exceptions import FailedValidation
from .utils import stac_jsonpath_match

# types
PathLike = Union[str, Path]
"""
Tasks can use parameters provided in a `process` Dictionary that is supplied in the ItemCollection
JSON under the "process" field. An example process definition:

```
{
    "description": "My process configuration"
    "upload_options": {
        "path_template": "s3://my-bucket/${collection}/${year}/${month}/${day}/${id}",
        "collections": {
            "landsat-c2l2": ""
        }
    },
    "tasks": [
        {
            "name": "task-name",
            "parameters": {
                "param": "value"
            }
        }
    ]
}
```
"""


class Task(ABC):

    name = "task"
    description = "A task for doing things"
    version = "0.1.0"

    def __init__(
        self: "Task",
        payload: Dict,
        workdir: Optional[PathLike] = None,
        save_workdir: Optional[bool] = False,
        skip_upload: Optional[bool] = False,
        skip_validation: Optional[bool] = False,
    ):
        # set up logger
        self.logger = logging.getLogger(self.name)

        # set this to avoid confusion in destructor if called during validation
        self._save_workdir = True

        # validate input payload...or not
        if not skip_validation:
            if not self.validate(payload):
                raise FailedValidation()

        # set instance variables
        self._save_workdir = save_workdir
        self._skip_upload = skip_upload
        self._payload = payload

        # create temporary work directory if workdir is None
        if workdir is None:
            self._workdir = Path(mkdtemp())
        else:
            self._workdir = Path(workdir)
            makedirs(self._workdir, exist_ok=True)

    def __del__(self):
        # remove work directory if not running locally
        if not self._save_workdir:
            self.logger.debug("Removing work directory %s", self._workdir)
            rmtree(self._workdir)

    @property
    def process_definition(self) -> Dict:
        return self._payload.get("process", {})

    @property
    def parameters(self) -> Dict:
        task_configs = self.process_definition.get("tasks", [])
        if isinstance(task_configs, List):
            # tasks is a list
            task_config = [cfg for cfg in task_configs if cfg["name"] == self.name]
            if len(task_config) == 0:
                task_config = {}
            else:
                task_config = task_config[0]
            return task_config.get("parameters", {})
        elif isinstance(task_configs, Dict):
            # tasks is a dictionary of parameters (deprecated)
            warnings.warn(
                "task configs is Dictionary (deprecated), convert to List ",
                DeprecationWarning,
                stacklevel=2,
            )
            return task_configs.get(self.name, {})

    @property
    def upload_options(self) -> Dict:
        return self.process_definition.get("upload_options", {})

    @property
    def items_as_dicts(self) -> List[Dict]:
        return self._payload.get("features", [])

    @property
    def items(self) -> ItemCollection:
        items_dict = {"type": "FeatureCollection", "features": self.items_as_dicts}
        return ItemCollection.from_dict(items_dict, preserve_dict=True)

    @classmethod
    def validate(cls, payload: Dict) -> bool:
        # put validation logic on input Items and process definition here
        return True

    @classmethod
    def add_software_version(cls, items: List[Dict]):
        processing_ext = (
            "https://stac-extensions.github.io/processing/v1.1.0/schema.json"
        )
        for i in items:
            if "stac_extensions" not in i:
                i["stac_extensions"] = []
            i["stac_extensions"].append(processing_ext)
            i["stac_extensions"] = list(set(i["stac_extensions"]))
            if "properties" not in i:
                i["properties"] = {}
            i["properties"]["processing:software"] = {cls.name: cls.version}
        return items

    def assign_collections(self):
        """Assigns new collection names based on"""
        for i, (coll, expr) in itertools.product(
            self._payload["features"],
            self.upload_options.get("collections", dict()).items(),
        ):
            if stac_jsonpath_match(i, expr):
                i["collection"] = coll

    def download_item_assets(
        self, item: Dict, path_template: Optional[str] = "${collection}/${id}", **kwargs
    ):
        """Download provided asset keys for all items in payload. Assets are saved in workdir in a
           directory named by the Item ID, and the items are updated with the new asset hrefs.

        Args:
            assets (Optional[List[str]], optional): List of asset keys to download. Defaults to all assets.
        """
        outdir = str(self._workdir / path_template)
        loop = asyncio.get_event_loop()
        item = loop.run_until_complete(
            download_item_assets(item, path_template=outdir, **kwargs)
        )
        return item

    def download_items_assets(
        self,
        items: List[Dict],
        path_template: Optional[str] = "${collection}/${id}",
        **kwargs
    ):
        outdir = str(self._workdir / path_template)
        loop = asyncio.get_event_loop()
        items = loop.run_until_complete(
            download_items_assets(self.items, path_template=outdir, **kwargs)
        )
        return items

    def upload_item_assets_to_s3(self, item: Dict, assets: Optional[List[str]] = None):
        if self._skip_upload:
            self.logger.warning("Skipping upload of new and modified assets")
            return item
        item = upload_item_assets_to_s3(item, assets=assets, **self.upload_options)
        return item

    # this should be in PySTAC
    @staticmethod
    def create_item_from_item(item):
        new_item = deepcopy(item)
        # create a derived output item
        links = [
            link["href"] for link in item.get("links", []) if link["rel"] == "self"
        ]
        if len(links) == 1:
            # add derived from link
            new_item["links"].append(
                {
                    "title": "Source STAC Item",
                    "rel": "derived_from",
                    "href": links[0],
                    "type": "application/json",
                }
            )
        return new_item

    @abstractmethod
    def process(self, **kwargs) -> List[Dict]:
        """Main task logic - virtual

        Returns:
            [type]: [description]
        """
        # download assets of interest, this will update self.items
        # self.download_assets(['key1', 'key2'])
        # do some stuff
        # self.upload_assets(['key1', 'key2'])
        pass

    @classmethod
    def handler(cls, payload: Dict, **kwargs) -> "Task":
        if "href" in payload or "url" in payload:
            # read input
            with fsspec.open(payload.get("href", payload.get("url"))) as f:
                payload = json.loads(f.read())

        task = cls(payload, **kwargs)
        try:
            items = task.process(**task.parameters)

            # should this be included in process ?
            task._payload["features"] = cls.add_software_version(items)
            task.assign_collections()

            return task._payload
        except Exception as err:
            task.logger.error(err, exc_info=True)
            raise err

    @classmethod
    def parse_args(cls, args):
        dhf = argparse.ArgumentDefaultsHelpFormatter
        parser0 = argparse.ArgumentParser(description=cls.description)
        parser0.add_argument(
            "--version",
            help="Print version and exit",
            action="version",
            version=cls.version,
        )

        pparser = argparse.ArgumentParser(add_help=False)
        pparser.add_argument(
            "--logging", default="INFO", help="DEBUG, INFO, WARN, ERROR, CRITICAL"
        )

        subparsers = parser0.add_subparsers(dest="command")

        # run
        h = "Process STAC Item Collection"
        parser = subparsers.add_parser(
            "run", parents=[pparser], help=h, formatter_class=dhf
        )
        parser.add_argument(
            "input", help="Full path of item collection to process (s3 or local)"
        )

        h = "Write output payload to this URL"
        parser.add_argument("--output", help=h, default=None)

        # additional options
        h = "Use this as work directory. Will be created."
        parser.add_argument("--workdir", help=h, default=None, type=Path)
        h = "Save workdir after completion"
        parser.add_argument(
            "--save-workdir", dest="save_workdir", action="store_true", default=False
        )
        h = "Skip uploading of any generated assets and resulting STAC Items"
        parser.add_argument(
            "--skip-upload", dest="skip_upload", action="store_true", default=False
        )
        h = "Skip validation of input payload"
        parser.add_argument(
            "--skip-validation",
            dest="skip_validation",
            action="store_true",
            default=False,
        )
        h = """ Run local mode
                (save-workdir = True, skip-upload = True, skip-validation = True,
                workdir = 'local-output', output = 'local-output/output-payload.json') """
        parser.add_argument("--local", help=h, action="store_true", default=False)

        # turn Namespace into dictionary
        pargs = vars(parser0.parse_args(args))
        # only keep keys that are not None
        pargs = {k: v for k, v in pargs.items() if v is not None}

        if pargs.pop("local", False):
            # local mode sets all of
            for k in ["save_workdir", "skip_upload", "skip_validation"]:
                pargs[k] = True
            if pargs.get("workdir") is None:
                pargs["workdir"] = "local-output"
            if pargs.get("output") is None:
                pargs["output"] = Path(pargs["workdir"]) / "output-payload.json"

        if pargs.get("command", None) is None:
            parser.print_help()
            sys.exit(0)

        return pargs

    @classmethod
    def cli(cls):
        args = cls.parse_args(sys.argv[1:])
        cmd = args.pop("command")

        # logging
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

        if cmd == "run":
            href = args.pop("input")
            href_out = args.pop("output", None)

            # read input
            with fsspec.open(href) as f:
                payload = json.loads(f.read())

            # run task handler
            payload_out = cls.handler(payload, **args)

            # write output
            if href_out is not None:
                with fsspec.open(href_out, "w") as f:
                    f.write(json.dumps(payload_out))


# from https://pythonalgos.com/runtimeerror-event-loop-is-closed-asyncio-fix/
"""fix yelling at me error"""
from asyncio.proactor_events import _ProactorBasePipeTransport  # noqa
from functools import wraps  # noqa


def silence_event_loop_closed(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except RuntimeError as e:
            if str(e) != "Event loop is closed":
                raise

    return wrapper


_ProactorBasePipeTransport.__del__ = silence_event_loop_closed(
    _ProactorBasePipeTransport.__del__
)
"""fix yelling at me error end"""
