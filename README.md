# STAC Task (stactask)

This Python library consists of the Task class, which is used to create custom tasks based
on a "STAC In, STAC Out" approach. The Task class acts as wrapper around custom code and provides
several convenience methods for modifying STAC Items, creating derived Items, and providing a CLI.

This library is currently under development and may not be a final standalone repo and may 
be merged into [stactools](https://github.com/stac-utils/stactools), 
see [#345](https://github.com/stac-utils/stactools/issues/345). It is based on a [branch of
cirrus-lib](https://github.com/cirrus-geo/cirrus-lib/tree/features/task-class) except
aims to be more generic.


## run tasks

```
$ docker-compose run task pytest -v -s tests
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
| tasks       | Map<string, Dict> | Dictionary of task parameters by task name |

#### collections

The collections dictionary provides a collection ID and JSONPath pattern for matching against STAC Items.
At the end of processing, before the final STAC Items are returned, the Task class can be used to assign
all of the Items to specific collection IDs. For each Item the JSONPath pattern for all collections will be
compared. The first match will cause the Item's Collection ID to be set to the provided value.

### tasks

The tasks field is a dictionary with an optional key for each task. If present, it contains a dictionary 
that is converted to a set of keywords and passed to the Task's `process` function. 
The documentation for each task will provide the list of available parameters.

```
{
    "tasks": {
        "task-a": {
            "param1": "value1"
        },
        "task-c": {
            "param2": "value2":
        }
    }
}
```

In the example above a task named `task-a` would have the `param1=value1` passed as a keyword, while `task-c`
would have `param2=value2` passed. If there were a `task-b` to be run it would not be passed any keywords.


### UploadOptions Object

| Field Name    | Type | Description |
| ------------- | ---- | ----------- |
| path_template | string | REQUIRED A string template for specifying the location of uploaded assets |
| public_assets | [str] | A list of asset keys that should be marked as public when uploaded |
| headers | Map<str, str> | A set of key, value headers to send when uploading data to s3 |
| s3_urls | bool | Controls if the final published URLs should be an s3 (s3://<bucket>/<key>) or https URL |

#### path_template

The path_template string is a way to control the output location of uploaded assets from a STAC Item using metadata from the Item itself. The template can contain fixed strings along with variables used for substitution. The following variables can be used in the template.

Example
```
{
    "description": "My process configuration",
    "collections": {
        "landsat-c2l2": ""
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
