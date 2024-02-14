import argparse
import asyncio
import itertools
import json
import logging
import os
import sys
import warnings
from abc import ABC, abstractmethod
from copy import deepcopy
from os import makedirs
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

import fsspec
from pystac import Item, ItemCollection

from .asset_io import (
    download_item_assets,
    download_items_assets,
    upload_item_assets_to_s3,
)
from .exceptions import FailedValidation
from .utils import stac_jsonpath_match

# types
PathLike = Union[str, Path]


class Task(ABC):
    """
    Tasks can use parameters provided in a `process` Dictionary that is supplied in
    the ItemCollection JSON under the "process" field. An example process
    definition:

    ```
    {
        "description": "My process configuration"
        "upload_options": {
            "path_template": "s3://my-bucket/${collection}/${year}/${month}/${day}/${id}",
            "collections": {
                "landsat-c2l2": ""
            }
        },
        "tasks": {
            "task-name": {
                "param": "value"
            }
        ]
    }
    ```
    """

    name = "task"
    description = "A task for doing things"
    version = "0.1.0"

    def __init__(
        self: "Task",
        payload: Dict[str, Any],
        workdir: Optional[PathLike] = None,
        save_workdir: Optional[bool] = None,
        skip_upload: bool = False,
        skip_validation: bool = False,
    ):
        self.logger = logging.getLogger(self.name)

        # validate input payload... or not
        if not skip_validation:
            if not self.validate(payload):
                raise FailedValidation()

        # set instance variables
        self._skip_upload = skip_upload
        self._payload = payload

        # create temporary work directory if workdir is None
        if workdir is None:
            self._workdir = Path(mkdtemp())
            # if we are using a temp workdir we want to rm by default
            self._save_workdir = save_workdir if save_workdir is not None else False
        else:
            self._workdir = Path(workdir).absolute()
            makedirs(self._workdir, exist_ok=True)
            # if a workdir was specified we don't want to rm by default
            self._save_workdir = save_workdir if save_workdir is not None else True

    @property
    def process_definition(self) -> Dict[str, Any]:
        process = self._payload.get("process", {})
        if isinstance(process, dict):
            return process
        else:
            raise ValueError(f"process is not a dict: {type(process)}")

    @property
    def parameters(self) -> Dict[str, Any]:
        task_configs = self.process_definition.get("tasks", [])
        if isinstance(task_configs, List):
            warnings.warn(
                "task configs is list, use a dictionary instead",
                DeprecationWarning,
                stacklevel=2,
            )
            task_config_list = [cfg for cfg in task_configs if cfg["name"] == self.name]
            if len(task_config_list) == 0:
                return {}
            else:
                task_config: Dict[str, Any] = task_config_list[0]
                parameters = task_config.get("parameters", {})
                if isinstance(parameters, dict):
                    return parameters
                else:
                    raise ValueError(f"parameters is not a dict: {type(parameters)}")
        elif isinstance(task_configs, Dict):
            config = task_configs.get(self.name, {})
            if isinstance(config, dict):
                return config
            else:
                raise ValueError(
                    f"task config for {self.name} is not a dict: {type(config)}"
                )
        else:
            raise ValueError(f"unexpected value for 'tasks': {task_configs}")

    @property
    def upload_options(self) -> Dict[str, Any]:
        upload_options = self.process_definition.get("upload_options", {})
        if isinstance(upload_options, dict):
            return upload_options
        else:
            raise ValueError(f"upload_options is not a dict: {type(upload_options)}")

    @property
    def items_as_dicts(self) -> List[Dict[str, Any]]:
        features = self._payload.get("features", [])
        if isinstance(features, list):
            return features
        else:
            raise ValueError(f"features is not a list: {type(features)}")

    @property
    def items(self) -> ItemCollection:
        items_dict = {"type": "FeatureCollection", "features": self.items_as_dicts}
        return ItemCollection.from_dict(items_dict, preserve_dict=True)

    @classmethod
    def validate(cls, payload: Dict[str, Any]) -> bool:
        """Validates the payload and returns True if valid. If invalid, raises
        ``stactask.exceptions.FailedValidation`` or returns False."""
        # put validation logic on input Items and process definition here
        return True

    @classmethod
    def add_software_version(cls, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        warnings.warn(
            "add_software_version is deprecated, "
            "use add_software_version_to_item instead",
            DeprecationWarning,
        )
        modified_items = list()
        for item in items:
            modified_items.append(cls.add_software_version_to_item(item))
        return modified_items

    @classmethod
    def add_software_version_to_item(cls, item: Dict[str, Any]) -> Dict[str, Any]:
        """Adds software version information to a single item.

        Uses the processing extension.

        Args:
            item: A single STAC item

        Returns:
            Dict[str, Any]: The same item with processing information applied.
        """
        processing_ext = (
            "https://stac-extensions.github.io/processing/v1.1.0/schema.json"
        )
        if "stac_extensions" not in item:
            item["stac_extensions"] = []
        item["stac_extensions"].append(processing_ext)
        item["stac_extensions"] = list(set(item["stac_extensions"]))
        if "properties" not in item:
            item["properties"] = {}
        item["properties"]["processing:software"] = {cls.name: cls.version}
        return item

    def cleanup_workdir(self) -> None:
        """Remove work directory if configured not to save it"""
        try:
            if (
                not self._save_workdir
                and self._workdir
                and os.path.exists(self._workdir)
            ):
                self.logger.debug("Removing work directory %s", self._workdir)
                rmtree(self._workdir)
        except Exception as e:
            self.logger.warning(
                "Failed removing work directory %s: %s", self._workdir, e
            )

    def assign_collections(self) -> None:
        """Assigns new collection names based on"""
        for i, (coll, expr) in itertools.product(
            self._payload["features"],
            self.upload_options.get("collections", dict()).items(),
        ):
            if stac_jsonpath_match(i, expr):
                i["collection"] = coll

    def download_item_assets(
        self,
        item: Item,
        path_template: str = "${collection}/${id}",
        keep_original_filenames: bool = False,
        **kwargs: Any,
    ) -> Item:
        """Download provided asset keys for the given item. Assets are
        saved in workdir in a directory (as specified by path_template), and
        the items are updated with the new asset hrefs.

        Args:
            item (pystac.Item): STAC Item for which assets need be downloaded.
            assets (Optional[List[str]]): List of asset keys to download.
                Defaults to all assets.
            path_template (Optional[str]): String to be interpolated to specify
                where to store downloaded files.
            keep_original_filenames (Optional[bool]): Controls whether original
                file names should be used, or asset key + extension.
        """
        outdir = str(self._workdir / path_template)
        loop = asyncio.get_event_loop()
        item = loop.run_until_complete(
            download_item_assets(
                item,
                path_template=outdir,
                keep_original_filenames=keep_original_filenames,
                **kwargs,
            )
        )
        return item

    def download_items_assets(
        self,
        items: Iterable[Item],
        path_template: str = "${collection}/${id}",
        keep_original_filenames: bool = False,
        **kwargs: Any,
    ) -> List[Item]:
        """Download provided asset keys for the given items. Assets are
        saved in workdir in a directory (as specified by path_template), and
        the items are updated with the new asset hrefs.

        Args:
            items (List[pystac.Item]): List of STAC Items for which assets need
                be downloaded.
            assets (Optional[List[str]]): List of asset keys to download.
                Defaults to all assets.
            path_template (Optional[str]): String to be interpolated to specify
                where to store downloaded files.
            keep_original_filenames (Optional[bool]): Controls whether original
                file names should be used, or asset key + extension.
        """
        outdir = str(self._workdir / path_template)
        loop = asyncio.get_event_loop()
        items = loop.run_until_complete(
            download_items_assets(
                items,
                path_template=outdir,
                keep_original_filenames=keep_original_filenames,
                **kwargs,
            )
        )
        return list(items)

    def upload_item_assets_to_s3(
        self, item: Item, assets: Optional[List[str]] = None
    ) -> Item:
        if self._skip_upload:
            self.logger.warning("Skipping upload of new and modified assets")
            return item
        item = upload_item_assets_to_s3(item, assets=assets, **self.upload_options)
        return item

    # this should be in PySTAC
    @staticmethod
    def create_item_from_item(item: Dict[str, Any]) -> Dict[str, Any]:
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
    def process(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """Main task logic - virtual

        Returns:
            [type]: [description]
        """
        # download assets of interest, this will update self.items
        # do some stuff
        pass

    def post_process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Perform post-processing operations on an item.

        E.g. add software version information.

        Most tasks should prefer to not override this method, as logic should be
        kept in :py:meth:`Task.process`. If you do override this method, make
        sure to call ``super().post_process_item()`` AFTER doing any custom
        post-processing, so any regular behavior can take your changes into account.

        Args:
            item: An item produced by :py:meth:`Task.process`

        Returns:
            Dict[str, Any]: The item with any additional attributes applied.
        """
        item = self.add_software_version_to_item(item)
        assert "stac_extensions" in item
        assert isinstance(item["stac_extensions"], list)
        item["stac_extensions"].sort()
        return item

    @classmethod
    def handler(cls, payload: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        task = None
        try:
            if "href" in payload or "url" in payload:
                # read input
                with fsspec.open(payload.get("href", payload.get("url"))) as f:
                    payload = json.loads(f.read())

            task = cls(payload, **kwargs)
            try:
                items = list()
                for item in task.process(**task.parameters):
                    items.append(task.post_process_item(item))

                task._payload["features"] = items
                task.assign_collections()

                return task._payload
            except Exception as err:
                task.logger.error(err, exc_info=True)
                raise err
        finally:
            if task:
                task.cleanup_workdir()

    @classmethod
    def parse_args(cls, args: List[str]) -> Dict[str, Any]:
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
    def cli(cls) -> None:
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


def silence_event_loop_closed(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
    @wraps(func)
    def wrapper(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore
        try:
            return func(self, *args, **kwargs)
        except RuntimeError as e:
            if str(e) != "Event loop is closed":
                raise

    return wrapper


setattr(
    _ProactorBasePipeTransport,
    "__del__",
    silence_event_loop_closed(_ProactorBasePipeTransport.__del__),
)
"""fix yelling at me error end"""
