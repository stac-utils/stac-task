import importlib.util
import sys
from pathlib import Path

from ._registry import get_task, register_task
from .models import Anything, Nothing, Process
from .payload import Payload
from .task import (
    HrefTask,
    ItemTask,
    OneToManyTask,
    OneToOneTask,
    StacInStacOutTask,
    StacOutTask,
    Task,
    ToItemTask,
)
from .types import PathLikeObject


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
    "get_task",
    "register_task",
]
