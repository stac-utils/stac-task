from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, ClassVar, Dict, Generic, List, Optional, Type, TypeVar

import pystac
import pystac.utils
import stac_asset.blocking
from pydantic import BaseModel, Field

from .models import Anything, Href, Item

Input = TypeVar("Input", bound=BaseModel)
Output = TypeVar("Output", bound=BaseModel)


class Task(BaseModel, ABC, Generic[Input, Output]):
    """A generic task."""

    # Go away mypy, you can't handle this (it's not your fault,
    # https://github.com/python/mypy/issues/5144)
    input: ClassVar[Type[Input]] = Anything  # type: ignore
    """The input model."""

    output: ClassVar[Type[Output]] = Anything  # type: ignore
    """The output model."""

    payload_href: Optional[str] = None
    """The href of the payload that was used to execute this task."""

    working_directory: str = Field(default_factory=TemporaryDirectory)
    """The directory to save any downloaded files."""

    @abstractmethod
    def process(self, input: Input) -> List[Output]:
        """Processes an item with this task.

        Args:
            item: The input item. It could be anything.

        Result:
            List[Output]: The output items. They could be anything. A list is
                supported to allow a single input to generate multiple outputs
                (fanout).
        """
        ...

    def process_dict(self, input: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Processes a dictionary.

        This method handles the model validation. In general, subclasses should
        prefer to override `process`.

        Args:
            item: The input dictionary

        Result:
            List: A list of output dictionaries
        """
        return [
            output.model_dump()
            for output in self.process(self.input.model_validate(input))
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
        path = Path(self.working_directory) / Path(href).name
        with open(path, "wb") as f:
            # TODO async, or at least go chunk by chunk?
            f.write(stac_asset.blocking.read_href(href))
        return str(path)


class PassthroughTask(Task[Anything, Anything]):
    """A simple task that doesn't modify the items at all."""

    def process(self, input: Anything) -> List[Anything]:
        return [input]


class StacOutputTask(Task[Input, Item], ABC):
    """Anything in, STAC out task."""

    output = Item


class ItemTask(StacOutputTask[Item], ABC):
    """STAC In, STAC Out task.

    A abstract task that has STAC Items as the input and the output.
    """

    input = Item

    @abstractmethod
    def process_item(self, input: pystac.Item) -> pystac.Item:
        """Takes a :py:class:`pystac.Item` as input, and returns the same.

        Args:
            item: The input pystac item

        Returns:
            pystac.Item: A pystac item
        """
        ...

    def process(self, input: Item) -> List[Item]:
        return [Item.from_pystac(self.process_item(input.to_pystac()))]


class HrefTask(StacOutputTask[Href], ABC):
    """Href in, STAC Out task.

    A abstract task that takes a single href as input, and returns a pystac Item.
    """

    input = Href

    @abstractmethod
    def process_href(self, href: str) -> pystac.Item:
        """Takes an href as input, and returns a single pystac Item.

        Args:
            href: An input href

        Returns:
            pystac.Item: The output item
        """
        ...

    def process(self, input: Href) -> List[Item]:
        if self.payload_href:
            href = pystac.utils.make_absolute_href(
                input.href, self.payload_href, start_is_dir=False
            )
        else:
            href = input.href
        return [Item.from_pystac(self.process_href(href))]
