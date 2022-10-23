# STAC Task (stactask)

This Python library consists of the Task class, which is used to create custom tasks based
on a "STAC In, STAC Out" approach. The Task class acts as wrapper around custom code and provides
several convenience methods for modifying STAC Items, creating derived Items, and providing a CLI.

This library is currently under development and may not be a final standalone repo and may 
be merged into [stactools](https://github.com/stac-utils/stactools), 
see [#345](https://github.com/stac-utils/stactools/issues/345). It is based on a [branch of
cirrus-lib](https://github.com/cirrus-geo/cirrus-lib/tree/features/task-class) except
aims to be more generic.

## Quickstart for Creating New Tasks


```
from stactask import Task

class MyTask(Task):
    name = 'my-task'
    description = 'this task does it all'

    def validate(self):
        assert len(self.items) == 1

    def process(self):
        item = self.items[0]
        
        # download a datafile
        item = self.download_item_assets(item, assets=['data'])
        
        # operate on the local file to create a new asset


        item = self.upload_item_assets_to_s3(item)

        # this task returns a single item
        return [item]
```


## Task Input

| Field Name    | Type | Description |
| ------------- | ---- | ----------- |
| type          | string | Must be FeatureCollection |
| features      | [Item] | A list of STAC `Item` |
| process       | ProcessDefinition | A Process Definition |

## ProcessDefinition Object

A STAC task can be provided additional configuration via the 'process' field in the input 
ItemCollection.

| Field Name    | Type | Description |
| ------------- | ---- | ----------- |
| description | string | Optional description of the process configuration |
| collections   | Map<str, str> | A mapping of output collection name to a JSONPath pattern (for matching Items) |
| upload_options | UploadOptions | Options used when uploading assets to a remote server |
| tasks       | List[TaskConfig] OR Map<str, Dict> | Ordered List of task configurations  |

## TaskConfig Object

A Task Configuration contains information for running a specific task.

| Field Name    | Type | Description |
| ------------- | ---- | ----------- |
| name          | str  | **REQUIRED** Name of the task |
| parameters    | Map<str, str> | Dictionary of keyword parameters that will be passed to the Tasks `process` function |

Using a Dictionary for task_configs ("task_name": <ParametersDict>) is deprecated. Convert to
List of TaskConfig objects

#### collections

The collections dictionary provides a collection ID and JSONPath pattern for matching against STAC Items.
At the end of processing, before the final STAC Items are returned, the Task class can be used to assign
all of the Items to specific collection IDs. For each Item the JSONPath pattern for all collections will be
compared. The first match will cause the Item's Collection ID to be set to the provided value.

**Example**

```
    "collections": {
        "landsat-c2l2": "$[?(@.id =~ 'LC08.*')]"
    }
```

In this example, the task will set any STAC Items that have an ID beginning with "LC08" to the `landsat-c2l2` collection.

See [Jayway JsonPath Evaluator](https://jsonpath.herokuapp.com/) to experiment with JSONpath and [regex101](https://regex101.com/) to experiment with regex.

### tasks

The tasks field is a dictionary with an optional key for each task. If present, it contains 
a dictionary that is converted to a set of keywords and passed to the Task's `process` function.
The documentation for each task will provide the list of available parameters.

```
{
    "tasks": [
        {
            "name": "task-a",
            "parameters": {
                "param1": "value1"
            }
        },
        {
            "name": "task-c",
            "parameters": {
                "param2": "value2"
            }
        }
    ]
}
```

In the example above a task named `task-a` would have the `param1=value1` passed as a keyword, while `task-c`
would have `param2=value2` passed. If there were a `task-b` to be run it would not be passed any keywords.


### UploadOptions Object

| Field Name    | Type | Description |
| ------------- | ---- | ----------- |
| path_template | string | **REQUIRED** A string template for specifying the location of uploaded assets |
| public_assets | [str] | A list of asset keys that should be marked as public when uploaded |
| headers | Map<str, str> | A set of key, value headers to send when uploading data to s3 |
| s3_urls | bool | Controls if the final published URLs should be an s3 (s3://*bucket*/*key*) or https URL |

#### path_template

The path_template string is a way to control the output location of uploaded assets from a STAC Item using metadata from the Item itself. The template can contain fixed strings along with variables used for substitution. The following variables can be used in the template.

See [https://jsonpath.herokuapp.com/](Jayway JsonPath Evaluator) to experiment with JSONpath and [https://regex101.com/](regex101) to experiment with regex

**Full Payload Example**
```
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


## Development

### run tests

```
$ pytest -v -s tests
```