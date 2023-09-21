# stac-task

Python framework for writing tasks to create and modify [STAC](https://stacspec.org/) items.

## Installation

```shell
pip install stac-task[cli]
```

If you'd like to use **stac-task** in a downstream library or application, you can omit the `cli` optional dependency to avoid installing [click](https://click.palletsprojects.com).

## Quickstart

To write your own task, pick one of the [available base tasks](#tasks), subclass it, and write your logic.
You can define your input and output schemas using [pydantic](https://docs.pydantic.dev/) models.
The base `Task` class takes a list of inputs and returns a list of outputs, and subclasses provide simpler interfaces for similar operations:

```python
import stac_task
from pystac import Item
from stac_task import ItemTask

class MyTask(ItemTask):
    def process_item(self, item: Item) -> Item:
        item.properties["foo"] = "bar"
        return item

# Tasks need to be registered so they can be executed by `Process.execute`
stac_task.register_task("my-task", MyTask)
```

To run a task from the command-line, you can use the `-f` flag to load your script and register your task for execution:

```shell
stac-task -f my_task.py run payload.json
```

Of course, this is a STAC-centric framework, so you're probably looking to create STAC items.
Use `StacInStacOutTask` to process a list of STAC items to produce another list.
Use `ItemTask` to process one STAC item into another STAC item.

## Payloads

The task inputs and parameters are defined by a `Payload`.
Here is a very simple payload:

```json
{
    "features": [
        {"name": "First"},
        {"name": "Last"},
    ],
    "process": {
        "tasks": {
            "my-task" {
                "lower": true
            }
        }
    }
}
```

And here's a task that coalesces those two input features into a single output feature:

```python
import stac_task
from pydantic import BaseModel
from stac_task import Task

class MyTaskInput(BaseModel):
    name: str

class MyTaskOutput(BaseModel):
    name: str
    length: int

class MyTask(Task[MyTaskInput, MyTaskOutput]):
    lower: bool = False

    def process(self, input: List[MyTaskInput]) -> List[MyTaskOutput]:
        name = " ".join(value.name for value in input)
        if self.lower:
            name = name.lower()
        return [MyTaskOutput(name=name, length=len(name))]

stac_task.register_task("my-task", MyTask)
```

## Tasks

These are the available base tasks.
Each class name links to its API documentation.

| Class | Key method | Description |
| -- | -- | -- |
| `Task` | `process(self, input: List[Any]) -> List[Any]` | The most flexible task. |
| `StacOutTask` | `process_to_items(self, input: List[Any]) -> List[Item]` | Creates a list of STAC items from a list of any inputs |
| `StacInStacOutTask` | `process_items(self, input: List[Item]) -> List[Item]` | Creates a list of STAC items from a list of STAC items |
| `OneToManyTask` | `process_one_to_many(self, input: Any) -> List[Any]` | Creates many things from one thing |
| `OneToOneTask` | `process_one_to_one(self, input: Any) -> Any` | Creates one thing from one thing |
| `ToItemTask` | `process_to_item(self, input: Any) -> Item` | Creates a STAC item from one thing |
| `ItemTask` | `process_item(self, item: Item) -> Item` | Creates a new STAC item from an input STAC item |
| `HrefTask` | `process_href(self, href: str) -> Item` | Creates a STAC item from a single href |

## Running tasks

There are (at least) three different ways to define and run your tasks

The simplest is to write your task in its own file, then load it into the CLI: `stac-task -f my_task.py run payload.json`.
You can also use an `if __name__ == "__main__"` check and then execute your file directly, e.g. `python -m my_task.py`; see [examples/rio_stac_task_standalone.py](examples/rio_stac_task_standalone.py) for how this might look in practice.

If your task is more complex, you can wrap it in its own package.
We use package metadata, as described in the [Python packaging guide](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/#using-package-metadata), to discover plugins.
In your `pyproject.toml`, use the `stac_task.plugins` entrypoint:

```toml
[project.entry-points.'stac_task.plugins']
my_task = "my_task"
```

Again, see [the `examples/` directory](examples/rio_stac_task/pyproject.toml) for an example.
