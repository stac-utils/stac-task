# STAC Task User Guide

This guide provides a comprehensive overview of building and running **STAC Tasks** using the [`stac-task`](https://github.com/stac-utils/stac-task) library. Following the "STAC In, STAC Out" philosophy, a STAC Task is a discrete unit of processing that consumes STAC metadata via a Cirrus process payload, performs an operation (_e.g._, data transformation, metadata generation), and outputs updated STAC metadata.

The objective of this document is to provide basic instructions as to how to create and run a STAC Task and to provide a basic look under-the-hood of `stac-task`.

---

## Table of Contents

1. [The STAC Task Philosophy](#the-stac-task-philosophy)
2. [Project Anatomy](#project-anatomy)
3. [Task Workflow](#task-workflow)
3. [The Task Class](#the-task-class)
* [The Task Module](#the-task-module)
* [The Task Object](#the-task-object)
* [The `process` Method](#the-process-method)


4. [Configuration and the Cirrus Payload](#configuration-and-the-cirrus-payload)
* [The `process_definition` Object](#the-process_definition-object)
* [The Payload Object](#the-payload-object)


5. [Convenience Features](#convenience-features)
* [Built-in Logger and S3 Object](#built-in-logger-and-s3-object)
* [Uploading Assets and Items](#uploading-assets-and-items)


6. [Entry Points: Handler and CLI](#entry-points-handler-and-cli)
7. [Running a STAC Task](#running-a-stac-task)
8. [External Resources](#external-resources)

---

## The STAC Task Philosophy

The core principle of a STAC Task is **STAC In, STAC Out**.

* **Input:** A list of one or more STAC Items.
* **Output:** A list of modified or newly created STAC Items.

This approach (a) avoids passing (potentially large) datasets from task to task and (b) makes metadata central to data processing thus improving process documentation and data provenance.  By standardizing on STAC, tasks become modular components that can be chained together in complex workflows (like [Cirrus](https://github.com/cirrus-geo/cirrus-geo)) without needing custom glue code between every step.  `stac-task` is built for Cirrus workflows, but, aside from accepting a properly formatted Cirrus process payload (see [Configuration and the Cirrus Payload](#configuration-and-the-cirrus-payload), below), can run independently (either locally or cloud-deployed).

---

## Project Anatomy

A STAC Task project follows the typical Python project structure - the tree below shows a minimal example of a valid STAC task project:

```text
my-stac-task/
├── src/
│   └── my_task/
│       ├── __init__.py
│       └── task.py       # The core logic
├── tests/
│   └── test_task.py      # Local testing logic
├── pyproject.toml        # Dependency management (uv/pip)
└── Dockerfile            # Containerization for cloud deployment

```

---

## The Basics

Once you have a properly structured and configured project set-up (based on the `my-stac-task` template or otherwise), your job as a STAC Task developer is straightforward:
* You are adding business logic to the `task` module (or calling other modules that you develop)
* You are testing your code

Your task can be run in a few different ways depending on your particular needs:

Via the CLI:
```bash
my-stac-task run input_payload.json
```

Via the handler:
```python
output_payload = MyStacTask.handler(payload=input_payload)
```

By running the task module as a script:
```bash
python src/my_task/task.py run input_payload.json
```
(In reality, this is just another way of calling `Task.handler`...)

See the [Entry Points](#entry-points-handler-and-cli) section below for more detail.

---

## Task Workflow

Once you have a Cirrus process payload (including its STAC Items, if applicable) the user workflow is very straightforward:
1. Initiate the Task (via the handler or the CLI)
* pass in the payload
2. The Task runs
* an output payload is returned
(See [Running a STAC Task](#running-a-stac-task), below, for more details.)

For additional context, this is the basic internal STAC Task workflow:
1. The task is initiated by passing in a Cirrus process payload
* by the `handler` function, or
* by the `CLI` 
2. The `stactask.Task.handler` _class method_ is called (not to be confused with any handler _function_...)
* the Task is instantiated with a payload
* the payload is validated
* task and workflow parameters are extracted
3. The process method is called
* all user-defined processing executes
* optionally:
   * STAC Items are created or adjusted
   * payload parameters are created, adjusted, etc.
4. A list of one or more STAC Items is returned
5. STAC Items are added to the Cirrus process payload
6. The updated Cirrus process payload is returned

---

## The Task Class

### The Task Module

The `task` module (task.py) contains the core source code for a STAC task and has somewhat strict requirements for its contents:
* the Task sub-class object (which inherits from `stactask.Task`)
* the `process` method of the Task
* the `handler` function which calls the `stactask.Task.handler` method

### The Task Object

Every task must inherit from `stactask.Task` - this passes on all of the core functionality of `stac-task` to your task. You define a class where you set the task's name and description, then implement the logic.

```python
from stactask import Task
from typing import List, Any
from pystac import Item

class MyStacTask(Task):
    name = "my-processing-task"
    description = "This Task is an example"
    version = "2025.03.02"

    def process(self, **kwargs: Any) -> List[Item]:
        return self.items_as_dicts
```

The Task object is instantiated when the task code is first executed. A Cirrus process payload optionally containing STAC Items and parameters for various workflow and task processes is passed in to the Task object and can be retrieved via `self.payload`.

### The `process` Method

The `process` method is the heart of your task - this is where any business logic is called. `process` should always return a list of STAC Items as Python dictionaries.

```python
def process(self, **kwargs: Any) -> List[str]:
    for item in self.items:
        self.logger.info(f"Processing item: {item.id}")
        
        # Example logic: Add a custom property
        item.properties["my_task:status"] = "processed"
        
    return [item.to_dict() for item in items]
```
Note: the `kwargs` argument exists in the `process` method to facilitate passing in task and workflow option parameters internally within `stactask.Task` - it must remain in the local method definition...

### The Handler Function

The `handler` function acts as the entry point for AWS Lambda or other event-driven systems. Object naming here is less strict and might depend on requirements for the compute environment (_e.g._ `lambda_handler()` should be the name if the Task is intended for AWS Lambda). It takes the raw JSON payload as an event and passes it to the `stactask.Task.handler` class method which manages the lifecycle of the task.

```python
def handler(event: dict, context: dict = {}):
    return MyStacTask.handler(payload=event)
```

---

## Configuration and the Cirrus Payload

### The Cirrus Process Payload

The Cirrus process payload is a JSON structure containing any incoming STAC Items and any externally-defined task and workflow parameters.  Cirrus workflows use the payload to track the state of a workflow. `stac-task` abstracts this so you mainly deal with the `items` and `process_definition` (see below).

For deeper details on payload structure, see the [Cirrus Payload Documentation](https://cirrus-geo.github.io/cirrus-geo/v0.15.4/index.html).

This is an example payload for reference:

```json
{
    "type": "FeatureCollection",
    "features": [
        {
            <stac-item>
        }
    ],
    "process": [
        {
            "description": "My process configuration",
            "tasks": {
                "my-stac-task": {
                    "param": "value"
                },
                "the-next-task-in-the-workflow": {
                    "next-param": "value",
                }
            },
            "workflow_options": {
                "global_param": "global_value"
            },
            "upload_options": {
                "path_template": "s3://my-bucket/${collection}/${year}/${month}/${day}/${id}",
            },
            "collection_matchers": [
                <collection-matcher-object>
            ],
            "collection_options": {
                "my-collection": {
                    "upload_options": {
                        "path_template": "s3://my-bucket/${collection}/${mgrs:utm_zone}/${mgrs:latitude_band}/${mgrs:grid_square}/${year}/${month}/${id}",
                    }
                }
            }
        }
    ]
}
```

* `type`: the JSON object is actually a GeoJSON FeatureCollection wiht an additional `process` field
* `features`: if present, contains STAC Item(s)
* `process`: process definition containing task, workflow, and upload options - the process definition is exposed as `self.process_definition` in the `Task` object.
   * `tasks`: contains custom parameters on a per-task basis - in this example the `my-stac-task` key points to custom parameters for this task
   * `workflow_options`: contains custom parameters applicable across an entire workflow (_e.g._ to this task, `my-stac-task` and any other STAC Tasks in the same workflow)
   * `upload_options`: contains the configuration for data / metadata upload, most notably `path_template`, a convenience URL template that uses strings derived from STAC Item property fields (collection, id, etc.) to define an upload path
   * `collection_matchers`: CollectionMatcher objects search for a JSONPath pattern within a STAC Item and assign a collection based on a match (for instance, if a STAC Item's properties included `"producer": "usgs"` the collection matcher would identify that with `$[?(@.properties.producer == 'usgs')]` and assign a collection to the Item accordingly)
   * `collection_options`: collection-specific configuration options (primarily used for collection-specific upload options)

### The `process_definition` Object

Within your class, process payload parameters are accessible via `self.process_definition`. This allows you to pass dynamic settings to your task without changing the code.

```python
# In your code:
def process(self, **kwargs: Any) -> List[Item]:
    # Access a parameter defined in the Cirrus workflow
    threshold = self.process_definition.get("threshold", 0.5)
    ...

```

---

## Convenience Features

The `Task` base class provides several built-in utilities to simplify cloud-based geospatial work.

add_software_version_to_item - Adds software version information to a single item.  Uses the processing extension.
        item["properties"]["processing:software"] = {cls.name: cls.version}

assign_collections - Assigns new collection names based on collection_matchers or the legacy
        upload_options collections attribute according to the first matching
        expression in the order they are defined.

download_item_assets - Download provided asset keys for the given item. Assets are
        saved in workdir in a directory (as specified by path_template), and
        the items are updated with the new asset hrefs.

download_items_assets - Download provided asset keys for the given items. Assets are
        saved in workdir in a directory (as specified by path_template), and
        the items are updated with the new asset hrefs.

items - `pystac.ItemCollection` of the Items in the payload

items_as_dicts - Items in the features list of the payload as Python dictionaries

parameters - a dictionary of task and workflow parameters

process_definition - the Cirrus payload process block as a dictionary 

task_options - payload task options for this task

upload_item_assets_to_s3 - Upload Item assets to an S3 bucket; returns A new STAC Item with uploaded assets pointing to newly uploaded file URLs

upload_item_to_s3 - Upload the canonical version of the Item to S3

upload_options - payload upload options (note that this is the process-level options and not the collection-level options)

workflow_options - payload workflow options

### Built-in Logger and S3 Object

* **`self.logger`**: A pre-configured logger that includes task metadata.
* **`self.s3`**: A `boto3utils.s3` instance for easy reading/writing to AWS S3.

```python
def process(self, items: List[Item], **kwargs: Any) -> List[Item]:
    # Use the built-in logger
    self.logger.info("Downloading extra config from S3...")
    
    # Use the built-in s3 utility
    config_data = self.s3.read_json("s3://my-bucket/config.json")
    ...

```

### Uploading Assets and Items

After processing, you often need to upload local files to S3 and update the STAC Item's metadata to point to the new S3 locations.

* **`upload_item_assets()`**: Uploads all local files referenced in an Item's assets to S3 based on the `path_template` in your configuration.
* **`upload_item()`**: Uploads the Item JSON itself to S3.

```python
def process(self, items: List[Item], **kwargs: Any) -> List[Item]:
    processed_items = []
    for item in items:
        # 1. Logic to create a local file (e.g., 'output.tif')
        # 2. Add it to the item
        item.add_asset("data", pystac.Asset(href="output.tif"))
        
        # 3. Automatically upload local assets to S3 and update HREFs
        self.upload_item_assets(item)
        
        processed_items.append(item)
    return processed_items

```

---

## Entry Points: Handler and CLI

### The Handler

The `handler` method is a class method that acts as the entry point for AWS Lambda or other event-driven systems. It takes the raw JSON payload and manages the lifecycle of the task.

```python
# At the bottom of task.py
def handler(payload, context=None):
    return MyProcessingTask.handler(payload)

```

### The CLI

Including a CLI allows you to run and debug your task locally using a JSON file as input.

```python
if __name__ == "__main__":
    MyProcessingTask.cli()

```

## Running a STAC Task

### Running locally

```bash
python src/my_task/task.py run input_payload.json --local --workdir ./tmp

```

---

## External Resources

* **[stac-task GitHub](https://github.com/stac-utils/stac-task)**: Core library source.
* **[Cirrus Task Example](https://github.com/cirrus-geo/cirrus-task-example)**: The gold standard for task project structure.
* **[Cirrus Documentation](https://cirrus-geo.github.io/cirrus-geo/)**: Documentation for the broader pipeline framework.
* **[PySTAC](https://pystac.readthedocs.io/)**: The library used for manipulating STAC objects in Python.