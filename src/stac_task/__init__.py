import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, Type

from .errors import ExecutionError, StacTaskError
from .models import Process
from .payload import Payload
from .task import HrefTask, Input, ItemTask, Output, PassthroughTask, Task
from .types import PathLikeObject

_TASKS: Dict[str, Type[Task[Any, Any]]] = {"passthrough": PassthroughTask}


def get_tasks() -> Dict[str, Type[Task[Input, Input]]]:
    """Returns all tasks.

    Returns:
        Dict: All registered tasks
    """
    return copy.deepcopy(_TASKS)


def register_task(name: str, task_class: Type[Task[Input, Output]]) -> None:
    """Registers a new task with this package.

    Args:
        name: The name of the task, as it will be used in a payload
        task_class: The class of task that will be run
    """
    if name in _TASKS:
        raise ValueError(f"task is already registered: {name}")
    else:
        _TASKS[name] = task_class


def load_file(path: PathLikeObject) -> None:
    """Loads a new Python module into the `stac_tas.plugins` namespace.

    This can be used to load modules with tasks.

    Args:
        path: The string or Path that will be loaded
    """
    # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    module_name = (
        "stac_task.plugins." + Path(path).stem
    )  # FIXME this feels a little fragile
    if module_name in sys.modules:
        raise ValueError(f"module name is already imported: {module_name}")
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None:
        raise ValueError(
            f"could not build spec from file location: {module_name}, {path}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    if not spec.loader:
        raise ValueError(f"spec does not have a loader for module {module_name}")
    spec.loader.exec_module(module)


__all__ = [
    "ExecutionError",
    "HrefTask",
    "ItemTask",
    "Payload",
    "Process",
    "StacTaskError",
    "Task",
]
