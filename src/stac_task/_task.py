import shutil
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Dict, Generic, List, Optional, Type, TypeVar

import pystac.utils
import stac_asset.blocking
from pydantic import BaseModel
from stac_asset import Config

from .models import Href, Item

Input = TypeVar("Input", bound=BaseModel)
Output = TypeVar("Output", bound=BaseModel)


class Task(BaseModel, ABC, Generic[Input, Output]):
    """A generic task."""

    # Go away mypy, you can't handle this (it's not your fault,
    # https://github.com/python/mypy/issues/5144)
    input: ClassVar[Type[Input]]  # type: ignore
    """The input model."""

    output: ClassVar[Type[Output]]  # type: ignore
    """The output model."""

    payload_href: Optional[str] = None
    """The href of the payload that was used to execute this task."""

    working_directory: Optional[Path] = None
    """The directory to save any downloaded files.
    
    If it's none, and a download needs to happen, a new temporary directory will
    be created.
    """

    @abstractmethod
    def process(self, input: List[Input]) -> List[Output]:
        """Processes a list of items.

        Args:
            input: The input items. They could be anything.

        Result:
            Output: The output items. They could be anything.
        """
        ...

    def process_dicts(self, input: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processes a list of dictionaries.

        This method handles the model validation. In general, subclasses should
        prefer to override `process`.

        Args:
            input: The input dictionaries

        Result:
            List[Dict[str, Any]]: A list of output dictionaries
        """
        return [
            output.model_dump()
            for output in self.process([self.input.model_validate(d) for d in input])
        ]

    def download_href(self, href: str) -> str:
        """Download an href to the current working directory.

        The file will be the same, and it will overwrite any existing files with
        the same name.

        Args:
            href: The href to download

        Returns:
            str: The downloaded href
        """
        working_directory = self._get_working_directory()
        path = working_directory / Path(href).name
        with open(path, "wb") as f:
            # TODO async, or at least go chunk by chunk?
            f.write(stac_asset.blocking.read_href(href))
        return str(path)

    def download_item(
        self, item: pystac.Item, include: Optional[List[str]] = None
    ) -> pystac.Item:
        """Downloads an item to this task's working directory.

        Args:
            item: The pystac item
            include: Assets to include. If not provided, all assets are downloaded.

        Returns:
            pystac.Item: The pystac item, with updated hrefs to the downloaded
                assets.
        """
        working_directory = self._get_working_directory()
        return stac_asset.blocking.download_item(
            item, working_directory, config=Config(include=include or [])
        )

    def download_item_collection(
        self,
        item_collection: pystac.ItemCollection,
        include: Optional[List[str]] = None,
    ) -> pystac.ItemCollection:
        """Downloads an item collection to this task's working directory.

        Args:
            item_collection: The pystac item collection
            include: Assets to include. If not provided, all assets are downloaded.

        Returns:
            pystac.ItemCollection: The pystac item collection, with updated
                hrefs to the downloaded assets.
        """
        working_directory = self._get_working_directory()
        return stac_asset.blocking.download_item_collection(
            item_collection, working_directory, config=Config(include=include or [])
        )

    def upload_item(
        self, item: pystac.Item, destination: str, include_item: bool = True
    ) -> pystac.Item:
        """Uploads an item's assets to a destination.

        Args:
            item: The pystac item
            destination: The destination folder to write the assets (and item if
                `include_item` is True)
            include_item: Whether to write the item JSON as well

        Returns:
            pystac.Item: The pystac item, with updated hrefs to the uploaded
                assets.
        """
        return stac_asset.blocking.upload_item(item, destination, include_item)

    def _get_working_directory(self) -> Path:
        if self.working_directory:
            return self.working_directory
        else:
            self.working_directory = Path(tempfile.mkdtemp())
            return self.working_directory

    def cleanup(self) -> None:
        """Remove this task's working directory."""
        if self.working_directory:
            shutil.rmtree(self.working_directory, ignore_errors=True)


class StacOutTask(Task[Input, Item], ABC):
    """STAC output task.

    This task expects a list of anything, and produces a list of STAC items.
    """

    output = Item

    def process(self, input: List[Input]) -> List[Item]:
        return [Item.from_pystac(item) for item in self.process_to_items(input)]

    @abstractmethod
    def process_to_items(self, input: List[Input]) -> List[pystac.Item]:
        """Process a list of pystac items and returns another list.

        Args:
            input: The list of inputs

        Returns:
            List[pystac.Item]: A list of pystac items
        """
        ...


class StacInStacOutTask(StacOutTask[Item], ABC):
    """STAC input, STAC output task.

    This task expects a list of STAC items as its input, and produces a list of
    STAC items.
    """

    input = Item

    def process_to_items(self, input: List[Item]) -> List[pystac.Item]:
        return self.process_items([item.to_pystac() for item in input])

    @abstractmethod
    def process_items(self, input: List[pystac.Item]) -> List[pystac.Item]:
        """Process a list of pystac items and returns another list.

        Args:
            input: A list of pystac items

        Returns:
            List[pystac.Item]: A list of pystac items
        """
        ...


class OneToManyTask(Task[Input, Output], ABC):
    """Produce many outputs from one input.

    For now, if one call to `process_one_to_many` fails, the exception will be
    propagated. This may change in the future (e.g. to allow some failures).
    """

    def process(self, input: List[Input]) -> List[Output]:
        # TODO parallelize? allow some to error? etc...
        output = list()
        for value in input:
            output.extend(self.process_one_to_many(value))
        return output

    @abstractmethod
    def process_one_to_many(self, input: Input) -> List[Output]:
        """Process one input item, producing an arbitrary number of outputs.

        Args:
            input: A single input

        Returns:
            List[Output]: A list of outputs
        """
        ...


class OneToOneTask(Task[Input, Output], ABC):
    """A task that can operate on each input item independently output per input.

    For now, if one call to `process_one_to_one` fails, the exception will be
    propagated. This may change in the future (e.g. to allow some failures).
    """

    def process(self, input: List[Input]) -> List[Output]:
        # TODO parallelize? allow some to error? etc...
        output = list()
        for value in input:
            output.append(self.process_one_to_one(value))
        return output

    @abstractmethod
    def process_one_to_one(self, input: Input) -> Output:
        """Process one input item, producing one output item.

        Args:
            input: An input

        Returns:
            Output: The output
        """
        ...


class ToItemTask(OneToOneTask[Input, Item], ABC):
    """An anything in, STAC out task."""

    output = Item

    def process_one_to_one(self, input: Input) -> Item:
        return Item.from_pystac(self.process_to_item(input))

    @abstractmethod
    def process_to_item(self, input: Input) -> pystac.Item:
        """Process to a single pystac Item.

        Args:
            input: The input

        Result:
            pystac.Item: The output item
        """
        ...


class ItemTask(ToItemTask[Item], ABC):
    """A STAC in, STAC out task."""

    input = Item

    def process_to_item(self, input: Item) -> pystac.Item:
        return self.process_item(input.to_pystac())

    @abstractmethod
    def process_item(self, item: pystac.Item) -> pystac.Item:
        """Process a single pystac Item.

        Args:
            item: The input pystac item

        Result:
            pystac.Item: The output item
        """
        ...


class HrefTask(ToItemTask[Href], ABC):
    """A href in, STAC out task."""

    input = Href

    def process_to_item(self, input: Href) -> pystac.Item:
        if self.payload_href:
            href = pystac.utils.make_absolute_href(
                input.href, self.payload_href, start_is_dir=False
            )
        else:
            href = input.href
        return self.process_href(href)

    @abstractmethod
    def process_href(self, href: str) -> pystac.Item:
        """Process a single href.

        Args:
            href: The input href

        Result:
            pystac.Item: The output item
        """
        ...