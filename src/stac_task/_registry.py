from __future__ import annotations

import copy
from threading import Lock
from types import TracebackType
from typing import Any, Dict, Optional, Type

from ._task import Input, Output, Task


class Registry:
    tasks: Dict[str, Type[Task[Any, Any]]]
    lock: Lock

    def __init__(self) -> None:
        self.tasks = dict()
        self.lock = Lock()

    def get_task(self, name: str) -> Type[Task[Input, Output]]:
        with self.lock:
            if name not in self.tasks:
                raise ValueError(
                    f"task not found: {name} "
                    f"(available tasks: {', '.join(self.tasks.keys())})"
                )
            else:
                return self.tasks[name]

    def get_tasks(self) -> Dict[str, Type[Task[Input, Output]]]:
        with self.lock:
            return copy.deepcopy(self.tasks)

    def register_task(self, name: str, task_class: Type[Task[Any, Any]]) -> None:
        with self.lock:
            # TODO allow overwriting
            if name in self.tasks:
                raise ValueError(f"task is already registered: {name}")
            else:
                self.tasks[name] = task_class

    def unregister_task(self, name: str) -> None:
        with self.lock:
            # TODO allow overwriting
            if name not in self.tasks:
                raise ValueError(f"task is not registered: {name}")
            else:
                del self.tasks[name]


class RegistryContextManager:
    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        try:
            unregister_task(self.name)
        except ValueError:
            pass


_REGISTRY = Registry()


def get_task(name: str) -> Type[Task[Input, Output]]:
    """Returns a task by name.

    Raises a `ValueError` if the task is not registered.

    Args:
        name: The tak name

    Returns:
        Type[Task[Any, Any]]: The task
    """
    return _REGISTRY.get_task(name)


def get_tasks() -> Dict[str, Type[Task[Input, Output]]]:
    return _REGISTRY.get_tasks()


def register_task(
    name: str, task_class: Type[Task[Input, Output]]
) -> RegistryContextManager:
    """Registers a new task with this package.

    Can be used as a context manager, in which case the task will be
    de-registered at the end of the block.

    ```python
    with stac_task.register_task("my-task", MyTask):
        assert stac_task.get_task("my-task")  # <- OK

    stac_task.get_task("my-task")  # <- Raises a ValueError
    ```

    Args:
        name: The name of the task, as it will be used in a payload
        task_class: The class of task that will be run
    """
    _REGISTRY.register_task(name, task_class)
    return RegistryContextManager(name)


def unregister_task(name: str) -> None:
    """Unregisters a task.

    Args:
        name: The name of the task, as it will be used in a payload
    """
    _REGISTRY.unregister_task(name)
