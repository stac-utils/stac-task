"""Framework for defining operations that create STAC items."""

from ._load import file as load_file
from ._load import plugins as load_plugins
from ._payload import Payload
from ._registry import get_task, get_tasks, register_task
from ._task import (
    HrefTask,
    ItemTask,
    OneToManyTask,
    OneToOneTask,
    StacInStacOutTask,
    StacOutTask,
    Task,
    ToItemTask,
)
from .models import Anything, Nothing, Process

__all__ = [
    "Anything",
    "HrefTask",
    "ItemTask",
    "Nothing",
    "OneToManyTask",
    "OneToOneTask",
    "Payload",
    "Process",
    "StacInStacOutTask",
    "StacOutTask",
    "Task",
    "ToItemTask",
    "load_file",
    "load_plugins",
    "get_task",
    "get_tasks",
    "register_task",
]
