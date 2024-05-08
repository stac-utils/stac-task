import argparse
import asyncio
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
from typing import Any, Callable, Iterable, Optional, Union

import fsspec
from boto3utils import s3
from pystac import Asset, Item, ItemCollection

from .asset_io import (
    download_item_assets,
    download_items_assets,
    upload_item_assets_to_s3,
)
from .config import DownloadConfig
from .exceptions import FailedValidation
from .logging import TaskLoggerAdapter
from .utils import find_collection as utils_find_collection

# types
PathLike = Union[str, Path]


class DeprecatedStoreTrueAction(argparse._StoreTrueAction):
    def __call__(self, parser, namespace, values, option_string=None) -> None:  # type: ignore
        warnings.warn("Argument %s is deprecated." % self.option_strings)
        super().__call__(parser, namespace, values, option_string)


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
        payload: dict[str, Any],
        workdir: Optional[PathLike] = None,
        save_workdir: Optional[bool] = None,
        skip_upload: bool = False,  # deprecated
        skip_validation: bool = False,  # deprecated
        upload: bool = True,
        validate: bool = True,
    ):

        if not skip_validation and validate:
            if not self.validate(payload):
                raise FailedValidation()

        # set instance variables
        if skip_upload:
            self._upload = False
        else:
            self._upload = upload

        self._skip_upload = not upload  # deprecated
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

        self.logger = TaskLoggerAdapter(
            logging.getLogger(self.name),
            self._payload.get("id"),
        )

    @property
    def process_definition(self) -> dict[str, Any]:
        process = self._payload.get("process", {})
        if isinstance(process, dict):
            return process
        else:
            raise ValueError(f"process is not a dict: {type(process)}")

    @property
    def parameters(self) -> dict[str, Any]:
        task_configs = self.process_definition.get("tasks", [])
        if isinstance(task_configs, list):
            warnings.warn(
                "task configs is list, use a dictionary instead",
                DeprecationWarning,
                stacklevel=2,
            )
            task_config_list = [cfg for cfg in task_configs if cfg["name"] == self.name]
            if len(task_config_list) == 0:
                return {}
            else:
                task_config: dict[str, Any] = task_config_list[0]
                parameters = task_config.get("parameters", {})
                if isinstance(parameters, dict):
                    return parameters
                else:
                    raise ValueError(f"parameters is not a dict: {type(parameters)}")
        elif isinstance(task_configs, dict):
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
    def upload_options(self) -> dict[str, Any]:
        upload_options = self.process_definition.get("upload_options", {})
        if isinstance(upload_options, dict):
            return upload_options
        else:
            raise ValueError(f"upload_options is not a dict: {type(upload_options)}")

    @property
    def collection_mapping(self) -> dict[str, str]:
        collection_mapping = self.upload_options.get("collections", {})
        if isinstance(collection_mapping, dict):
            return collection_mapping
        else:
            raise ValueError(f"collections is not a dict: {type(collection_mapping)}")

    @property
    def items_as_dicts(self) -> list[dict[str, Any]]:
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
    def validate(cls, payload: dict[str, Any]) -> bool:
        """Validates the payload and returns True if valid. If invalid, raises
        ``stactask.exceptions.FailedValidation`` or returns False."""
        # put validation logic on input Items and process definition here
        return True

    @classmethod
    def add_software_version(cls, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
    def add_software_version_to_item(cls, item: dict[str, Any]) -> dict[str, Any]:
        """Adds software version information to a single item.

        Uses the processing extension.

        Args:
            item: A single STAC item

        Returns:
            dict[str, Any]: The same item with processing information applied.
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
        """Assigns new collection names based on upload_options collections attribute
        according to the first matching expression in the order they are defined."""
        for item in self._payload["features"]:
            if coll := utils_find_collection(self.collection_mapping, item):
                item["collection"] = coll

    def download_item_assets(
        self,
        item: Item,
        path_template: str = "${collection}/${id}",
        config: Optional[DownloadConfig] = None,
        keep_non_downloaded: bool = True,
    ) -> Item:
        """Download provided asset keys for the given item. Assets are
        saved in workdir in a directory (as specified by path_template), and
        the items are updated with the new asset hrefs.

        Args:
            item (pystac.Item): STAC Item for which assets need be downloaded.
            assets (Optional[list[str]]): List of asset keys to download.
                Defaults to all assets.
            path_template (Optional[str]): String to be interpolated to specify
                where to store downloaded files.
            keep_original_filenames (Optional[bool]): Controls whether original
                file names should be used, or asset key + extension.
        """
        return asyncio.get_event_loop().run_until_complete(
            download_item_assets(
                item,
                path_template=str(self._workdir / path_template),
                config=config,
                keep_non_downloaded=keep_non_downloaded,
            )
        )

    def download_items_assets(
        self,
        items: Iterable[Item],
        path_template: str = "${collection}/${id}",
        config: Optional[DownloadConfig] = None,
        keep_non_downloaded: bool = True,
    ) -> list[Item]:
        """Download provided asset keys for the given items. Assets are
        saved in workdir in a directory (as specified by path_template), and
        the items are updated with the new asset hrefs.

        Args:
            items (list[pystac.Item]): List of STAC Items for which assets need
                be downloaded.
            assets (Optional[list[str]]): List of asset keys to download.
                Defaults to all assets.
            path_template (Optional[str]): String to be interpolated to specify
                where to store downloaded files.
            keep_original_filenames (Optional[bool]): Controls whether original
                file names should be used, or asset key + extension.
        """
        return list(
            asyncio.get_event_loop().run_until_complete(
                download_items_assets(
                    items,
                    path_template=str(self._workdir / path_template),
                    config=config,
                    keep_non_downloaded=keep_non_downloaded,
                )
            )
        )

    def upload_item_assets_to_s3(
        self,
        item: Item,
        assets: Optional[list[str]] = None,
        s3_client: Optional[s3] = None,
    ) -> Item:
        if self._upload:
            item = upload_item_assets_to_s3(
                item=item, assets=assets, s3_client=s3_client, **self.upload_options
            )
        else:
            self.logger.warning("Skipping upload of new and modified assets")

        return item

    def _is_local_asset(self, asset: Asset) -> bool:
        return bool(asset.href.startswith(str(self._workdir)))

    def _get_local_asset_keys(self, item: Item) -> list[str]:
        return [
            key for key, asset in item.assets.items() if self._is_local_asset(asset)
        ]

    def upload_local_item_assets_to_s3(
        self,
        item: Item,
        s3_client: Optional[s3] = None,
    ) -> Item:
        return self.upload_item_assets_to_s3(
            item=item,
            assets=self._get_local_asset_keys(item),
            s3_client=s3_client,
        )

    # this should be in PySTAC
    @staticmethod
    def create_item_from_item(item: dict[str, Any]) -> dict[str, Any]:
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
    def process(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Main task logic - virtual

        Returns:
            [type]: [description]
        """
        # download assets of interest, this will update self.items
        # do some stuff
        pass

    def post_process_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Perform post-processing operations on an item.

        E.g. add software version information.

        Most tasks should prefer to not override this method, as logic should be
        kept in :py:meth:`Task.process`. If you do override this method, make
        sure to call ``super().post_process_item()`` AFTER doing any custom
        post-processing, so any regular behavior can take your changes into account.

        Args:
            item: An item produced by :py:meth:`Task.process`

        Returns:
            dict[str, Any]: The item with any additional attributes applied.
        """
        assert "stac_extensions" in item
        assert isinstance(item["stac_extensions"], list)
        item["stac_extensions"].sort()
        return item

    @classmethod
    def handler(cls, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
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
    def parse_args(cls, args: list[str]) -> dict[str, Any]:
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
        parser = subparsers.add_parser(
            "run",
            parents=[pparser],
            formatter_class=dhf,
            help="Process STAC Item Collection",
        )
        parser.add_argument(
            "input",
            nargs="?",
            help="Full path of item collection to process (s3 or local)",
        )

        parser.add_argument(
            "--output",
            default=None,
            help="Write output payload to this URL",
        )

        # additional options
        parser.add_argument(
            "--workdir",
            default=None,
            type=Path,
            help="Use this as work directory. Will be created.",
        )

        parser.add_argument(
            "--save-workdir",
            dest="save_workdir",
            action="store_true",
            default=False,
            help="Save workdir after completion",
        )

        # skips are deprecated in favor of boolean optionals
        parser.add_argument(
            "--skip-upload",
            dest="skip_upload",
            action=DeprecatedStoreTrueAction,
            default=False,
            help="DEPRECATED: Skip uploading of generated assets and STAC Items",
        )
        parser.add_argument(
            "--skip-validation",
            dest="skip_validation",
            action=DeprecatedStoreTrueAction,
            default=False,
            help="DEPRECATED: Skip validation of input payload",
        )

        parser.add_argument(
            "--upload",
            dest="upload",
            action="store_true",
            default=True,
            help="Upload generated assets and resulting STAC Items",
        )
        parser.add_argument(
            "--no-upload",
            dest="upload",
            action="store_false",
            help="Don't upload generated assets and resulting STAC Items",
        )
        parser.add_argument(
            "--validate",
            dest="validate",
            action="store_true",
            default=True,
            help="Validate input payload",
        )
        parser.add_argument(
            "--no-validate",
            dest="validate",
            action="store_false",
            help="Don't validate input payload",
        )

        parser.add_argument(
            "--local",
            action="store_true",
            default=False,
            help=""" Run local mode
(save-workdir = True, upload = False,
workdir = 'local-output', output = 'local-output/output-payload.json') """,
        )

        # turn Namespace into dictionary
        pargs = vars(parser0.parse_args(args))
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
            href = args.pop("input", None)
            href_out = args.pop("output", None)

            # read input
            if href is None:
                payload = json.load(sys.stdin)
            else:
                with fsspec.open(href) as f:
                    payload = json.loads(f.read())

            # run task handler
            payload_out = cls.handler(payload, **args)

            # write output
            if href_out is None:
                json.dump(payload_out, sys.stdout)
            else:
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
