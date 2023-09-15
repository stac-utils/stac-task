from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Mapping, Optional, Type

import pystac.utils
import stac_asset.blocking
from pydantic import BaseModel, Field

from .errors import ExecutionError
from .models import Process
from .task import Input, Output, Task
from .types import PathLikeObject


class Payload(BaseModel):
    """A payload describing the items and the tasks to be executed

    Pretty specific to [cirrus](https://github.com/cirrus-geo/)."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    """Must be FeatureCollection."""

    features: List[Dict[str, Any]] = []
    """A list of STAC items, or things sort of like STAC items."""

    process: Process = Process()
    """The process definition."""

    # TODO do we need to support `url` as well?
    href: Optional[str] = None
    """An optional href parameter, used in indirect payloads.
    
    Indirect payloads contain an href to a large payload living on s3.
    """

    self_href: Optional[str] = Field(default=None, exclude=True)
    """The location that the payload was read from.
    
    Used to resolve relative hrefs.
    """

    @classmethod
    def from_href(cls, href: str, allow_indrections: bool = True) -> Payload:
        """Loads a payload from an href.

        If the payload has an `href` attribute set, that href will be fetched.
        This is used for "indirect" payloads that point to large payloads that
        need to be stored on s3.

        Args:
            href: The href to load the payload from.
            allow_indirections: Whether to follow indirection links. Generally
                used only when recursively calling this function to prevent infinite
                indirection loops.

        Returns:
            Payload: The payload
        """
        # TODO we could go async with these
        payload = cls.model_validate_json(stac_asset.blocking.read_href(href))
        if payload.href and not payload.features:
            if allow_indrections:
                href = pystac.utils.make_absolute_href(
                    payload.href, href, start_is_dir=False
                )
                return cls.from_href(href, allow_indrections=False)
            else:
                raise ValueError("Multiple indirections are not supported")
        else:
            payload.self_href = href
            return payload

    def execute(self, tasks: Mapping[str, Type[Task[Input, Output]]]) -> Payload:
        """Executes this payload, returning the updated payload.

        Args:
            tasks: The tasks to use for processing.

        Returns:
            Payload: A new payload, with updated items.
        """
        matches = set(key for key in tasks.keys() if key in self.process.tasks)
        if len(matches) == 0:
            raise ExecutionError("no tasks to execute")
        elif len(matches) == 1:
            key = matches.pop()
            task_class = tasks[key]
            task = task_class(**self.process.tasks[key])
            task.payload_href = self.self_href
            items = list()
            # TODO async / thread pool
            for item in self.features:
                items.extend(task.process_dict(item))
            return Payload(
                features=items, process=self.process.model_copy(), self_href=None
            )
        else:
            raise ValueError(
                "multiple task execution not supported at this time: "
                + ",".join(sorted(matches))
            )

    def to_path(self, path: PathLikeObject) -> None:
        """Writes a payload a path.

        Args:
            path: The path to write the payload to.
        """
        Path(path).write_text(self.model_dump_json())
