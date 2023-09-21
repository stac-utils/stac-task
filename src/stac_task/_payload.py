from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Type

import pystac.utils
import stac_asset.blocking
from pydantic import BaseModel, Field

from . import _registry
from ._task import Input, Output, Task
from .models import Process
from .types import PathLikeObject


class Payload(BaseModel):
    """A payload describing the items and the tasks to be executed."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    """Must be FeatureCollection.
    
    TODO should we remove this, or make this optional, since inputs (in
    particular) aren't always features?
    """

    features: List[Dict[str, Any]] = []
    """A list of STAC items, or things sort of like STAC items."""

    process: Process = Process()
    """The process definition."""

    # TODO do we need to support `url` as well?
    href: Optional[str] = None
    """An optional href parameter, used for indirect payloads.
    
    Indirect payloads contain an href to a large payload living on s3.
    """

    self_href: Optional[str] = Field(default=None, exclude=True)
    """The location that the payload was read from.
    
    Used to resolve relative hrefs.
    """

    @classmethod
    def from_href(cls, href: str, allow_indirections: bool = True) -> Payload:
        """Loads a payload from an href.

        If the payload has an `href` attribute set and there are no features,
        the href will be fetched.  This is used for "indirect" payloads that
        point to large payloads that need to be stored on s3.

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
            if allow_indirections:
                href = pystac.utils.make_absolute_href(
                    payload.href, href, start_is_dir=False
                )
                return cls.from_href(href, allow_indirections=False)
            else:
                raise ValueError("Multiple indirections are not supported")
        else:
            payload.self_href = href
            return payload

    def execute(
        self, name: str, task_class: Optional[Type[Task[Input, Output]]] = None
    ) -> Payload:
        """Executes a task on this payload, returning the updated payload.

        Args:
            name: The name of the task to execute
            task_class: The task class to insatiate and execute. If not
                provided, the class will be looked up in the registry.

        Returns:
            Payload: A new payload, with the output items
        """
        if name not in self.process.tasks:
            raise ValueError(f"task is not configured in payload: {name}")
        config = self.process.tasks[name]
        if not isinstance(config, dict):
            raise ValueError(f"task config is not a dict: {name} is a {type(config)}")
        if not task_class:
            task_class = _registry.get_task(name)
        task = task_class(**config)
        task.payload_href = self.self_href
        features = task.process_dicts(self.features)
        payload = self.model_copy(deep=True, update={"features": features})
        return payload

    def to_path(self, path: PathLikeObject) -> None:
        """Writes a payload a path.

        Args:
            path: The path to write the payload to.
        """
        Path(path).write_text(self.model_dump_json())
