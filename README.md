<!-- omit from toc -->
# STAC Task (stac-task)

[![Build Status](https://github.com/stac-utils/stac-task/workflows/CI/badge.svg?branch=main)](https://github.com/stac-utils/stac-task/actions/workflows/continuous-integration.yml)
[![PyPI version](https://badge.fury.io/py/stac-task.svg)](https://badge.fury.io/py/stac-task)
[![Documentation Status](https://readthedocs.org/projects/stac-task/badge/?version=latest)](https://stac-task.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/stac-utils/stac-task/branch/main/graph/badge.svg)](https://codecov.io/gh/stac-utils/stac-task)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

- [Quickstart for Creating New Tasks](#quickstart-for-creating-new-tasks)
- [Task Input](#task-input)
  - [ProcessDefinition Object](#processdefinition-object)
    - [UploadOptions Object](#uploadoptions-object)
      - [path\_template](#path_template)
      - [collections](#collections)
    - [tasks](#tasks)
    - [TaskConfig Object](#taskconfig-object)
- [Full Process Definition Example](#full-process-definition-example)
- [Migration](#migration)
  - [0.4.x -\> 0.5.x](#04x---05x)
- [Development](#development)
- [Contributing](#contributing)

This Python library consists of the Task class, which is used to create custom tasks based
on a "STAC In, STAC Out" approach. The Task class acts as wrapper around custom code and provides
several convenience methods for modifying STAC Items, creating derived Items, and providing a CLI.

This library is based on a [branch of cirrus-lib](https://github.com/cirrus-geo/cirrus-lib/tree/features/task-class) except aims to be more generic.

## Quickstart for Creating New Tasks

```python
from typing import Any

from stactask import Task, DownloadConfig

class MyTask(Task):
    name = "my-task"
    description = "this task does it all"

    def validate(self, payload: dict[str, Any]) -> bool:
        return len(self.items) == 1

    def process(self, **kwargs: Any) -> list[dict[str, Any]]:
        item = self.items[0]

        # download a datafile
        item = self.download_item_assets(
            item,
            config=DownloadConfig(include=['data'])
        )

        # operate on the local file to create a new asset
        item = self.upload_item_assets_to_s3(item)

        # this task returns a single item
        return [item.to_dict(include_self_link=True, transform_hrefs=False)]
```

## Task Input

| Field Name | Type              | Description               |
| ---------- | ----------------- | ------------------------- |
| type       | string            | Must be FeatureCollection |
| features   | [Item]            | A list of STAC `Item`     |
| process    | ProcessDefinition | A Process Definition      |

### ProcessDefinition Object

A STAC task can be provided additional configuration via the 'process' field in the input
ItemCollection.

| Field Name     | Type          | Description                                                                                                                                                                    |
| -------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| description    | string        | Optional description of the process configuration                                                                                                                              |
| upload_options | UploadOptions | Options used when uploading assets to a remote server                                                                                                                          |
| tasks          | Map<str, Map> | Dictionary of task configurations. A list of [task configurations](#taskconfig-object) is supported for backwards compatibility reasons, but a dictionary should be preferred. |

#### UploadOptions Object

| Field Name    | Type          | Description                                                                             |
| ------------- | ------------- | --------------------------------------------------------------------------------------- |
| path_template | string        | **REQUIRED** A string template for specifying the location of uploaded assets           |
| public_assets | [str]         | A list of asset keys that should be marked as public when uploaded                      |
| headers       | Map<str, str> | A set of key, value headers to send when uploading data to s3                           |
| collections   | Map<str, str> | A mapping of output collection name to a JSONPath pattern (for matching Items)          |
| s3_urls       | bool          | Controls if the final published URLs should be an s3 (s3://*bucket*/*key*) or https URL |

##### path_template

The path_template string is a way to control the output location of uploaded assets from a STAC Item using metadata from the Item itself.
The template can contain fixed strings along with variables used for substitution.
See [the PySTAC documentation for `LayoutTemplate`](https://pystac.readthedocs.io/en/stable/api/layout.html#pystac.layout.LayoutTemplate) for a list of supported template variables and their meaning.

##### collections

The collections dictionary provides a collection ID and JSONPath pattern for matching against STAC Items.
At the end of processing, before the final STAC Items are returned, the Task class can be used to assign
all of the Items to specific collection IDs. For each Item the JSONPath pattern for all collections will be
compared. The first match will cause the Item's Collection ID to be set to the provided value.

For example:

```json
"collections": {
    "landsat-c2l2": "$[?(@.id =~ 'LC08.*')]"
}
```

In this example, the task will set any STAC Items that have an ID beginning with "LC08" to the `landsat-c2l2` collection.

See [JSONPath Online Evaluator](https://jsonpath.com) to experiment with JSONPath and [regex101](https://regex101.com) to experiment with regex.

#### tasks

The tasks field is a dictionary with an optional key for each task. If present, it contains
a dictionary that is converted to a set of keywords and passed to the Task's `process` function.
The documentation for each task will provide the list of available parameters.

```json
{
    "tasks": {
        "task-a": {
            "param1": "value1"
        },
        "task-c": {
            "param2": "value2"
        }
    }
}
```

In the example above a task named `task-a` would have the `param1=value1` passed as a keyword, while `task-c`
would have `param2=value2` passed. If there were a `task-b` to be run it would not be passed any keywords.

#### TaskConfig Object

**DEPRECATED**: `tasks` should be a dictionary of parameters, with task names as keys. See [tasks](#tasks) for more information.

A Task Configuration contains information for running a specific task.

| Field Name | Type          | Description                                                                          |
| ---------- | ------------- | ------------------------------------------------------------------------------------ |
| name       | str           | **REQUIRED** Name of the task                                                        |
| parameters | Map<str, str> | Dictionary of keyword parameters that will be passed to the Tasks `process` function |

## Full Process Definition Example

Process definitions are sometimes called "Payloads":

```json
{
    "description": "My process configuration",
    "collections": {
        "landsat-c2l2": "$[?(@.id =~ 'LC08.*')]"
    },
    "upload_options": {
        "path_template": "s3://my-bucket/${collection}/${year}/${month}/${day}/${id}"
    },
    "tasks": {
        "task-name": {
            "param": "value"
        }
    }
}
```

## Migration

### 0.4.x -> 0.5.x

In 0.5.0, the previous use of fsspec to download Item Assets has been replaced with
the stac-asset library. This has necessitated a change in the parameters
that the download methods accept.

The primary change is that the Task methods `download_item_assets` and
`download_items_assets` (items plural) now accept fewer explicit and implicit
(kwargs) parameters.

Previously, the methods looked like:

```python
  def download_item_assets(
        self,
        item: Item,
        path_template: str = "${collection}/${id}",
        keep_original_filenames: bool = False,
        **kwargs: Any,
    ) -> Item:
```

but now look like:

```python
    def download_item_assets(
        self,
        item: Item,
        path_template: str = "${collection}/${id}",
        config: Optional[DownloadConfig] = None,
    ) -> Item:
```

Similarly, the `asset_io` package methods were previously:

```python
async def download_item_assets(
    item: Item,
    assets: Optional[list[str]] = None,
    save_item: bool = True,
    overwrite: bool = False,
    path_template: str = "${collection}/${id}",
    absolute_path: bool = False,
    keep_original_filenames: bool = False,
    **kwargs: Any,
) -> Item:
```

and are now:

```python
async def download_item_assets(
    item: Item,
    path_template: str = "${collection}/${id}",
    config: Optional[DownloadConfig] = None,
) -> Item:
```

Additionally, `kwargs` keys were set to pass configuration through to fsspec. The most common
parameter was `requester_pays`, to set the Requester Pays flag in AWS S3 requests.

Many of these parameters can be directly translated into configuration passed in a
`DownloadConfig` object, which is just a wrapper over the `stac_asset.Config` object.

Migration of these various parameters to `DownloadConfig` are as follows:

- `assets`: set `include`
- `requester_pays`: set `s3_requester_pays` = True
- `keep_original_filenames`: set `file_name_strategy` to
  `FileNameStrategy.FILE_NAME` if True or `FileNameStrategy.KEY` if False
- `overwrite`: set `overwrite`
- `save_item`: none, Item is always saved
- `absolute_path`: none. To create or retrieve the Asset hrefs as absolute paths, use either
  `Item#make_all_asset_hrefs_absolute()` or `Asset#get_absolute_href()`

## Development

Clone, install in editable mode with development requirements, and install the **pre-commit** hooks:

```shell
git clone https://github.com/stac-utils/stac-task
cd stac-task
pip install -e '.[dev]'
pre-commit install
```

To run the tests:

```shell
pytest
```

To lint all the files:

```shell
pre-commit run --all-files
```

## Contributing

Use Github [issues](https://github.com/stac-utils/stac-task/issues) and [pull requests](https://github.com/stac-utils/stac-task/pulls).
