Usage
=====

.. _installation:
.. _a_simple_task_definition:
.. _cli_usage:
.. _api_usage:

Installation
------------

To use STAC Task, first install it using pip:

.. code-block:: console

   (.venv) $ pip install stactask


A simple task definition
------------------------

The intended use of stac-task is for a developer to extend the `stactask.Task` class. An trivial
example class that does is shown below, which accepts a payload containing a field `item_id` and
generates a STAC Item with this id.

.. code-block:: python

   #!/usr/bin/env python

   import logging
   import os
   from datetime import datetime, timezone
   from typing import Any

   from pystac import Item
   from stactask.exceptions import InvalidInput
   from stactask.task import Task


   class MyTask(Task):  # type: ignore
      name = "my-task"
      description = "Create STAC Items for payload"
      version = "v2024.02.01"

      # override from Task
      @classmethod
      def validate(cls, payload: dict[str, Any]) -> bool:
         if "item_id" not in payload:
               raise InvalidInput("Missing field 'item_id' in payload")
         return True

      # override from Task
      def process(self, **kwargs: Any) -> list[dict[str, Any]]:
         item = Item(
               id=self._payload["item_id"],
               geometry={
                  "type": "Polygon",
                  "coordinates": [
                     [
                           [100.0, 0.0],
                           [101.0, 0.0],
                           [101.0, 1.0],
                           [100.0, 1.0],
                           [100.0, 0.0],
                     ]
                  ],
               },
               bbox=None,
               datetime=datetime.now(timezone.utc),
               properties={},
         )

         return [item.to_dict()]

   # Support for running as a Lambda Function
   def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
      return MyTask.handler(event)  # type: ignore

   # Support for running as a CLI application
   if __name__ == "__main__":
      MyTask.cli()

The expected input looks like the following:

.. code-block:: json

   {
      "id": "my-task/workflow-my-task/5427299e5b635537f33c07e0ad32fb87",
      "item_id": "G23923",
      "process": {
         "upload_options": {
            "collections": {
               "my-collection": "$[?(@.id =~ '.*')]"
            }
         }
      }
   }

In Task, the `/process/upload_options/collections` mapping uses JSONPath to map attributes of the
output Item to the collection that should be assigned to it. In this case, we only have one defined
that matches on any `id` value, and sets the collection to `my-collection`.

Running this with `python my-task.py run --local in.json` results in the following
output JSON, which has modified the payload to add a new
`features` attribute array.

.. code-block:: json

   {
      "id": "my-task/workflow-my-task/5427299e5b635537f33c07e0ad32fb87",
      "item_id": "G23923",
      "process": {
         "upload_options": {
            "collections": {
            "my-collection": "$[?(@.id =~ '.*')]"
            }
         }
      },
      "features": [
         {
            "type": "Feature",
            "stac_version": "1.0.0",
            "id": "G23923",
            "properties": {
            "datetime": "2024-04-04T13:55:05.598886Z",
            "processing:software": {
               "my-task": "v2024.02.01"
            }
            },
            "geometry": {
            "type": "Polygon",
            "coordinates": [
               [
                  [ 100.0, 0.0 ],
                  [ 101.0, 0.0 ],
                  [ 101.0, 1.0 ],
                  [ 100.0, 1.0 ],
                  [ 100.0, 0.0 ]
               ]
            ]
            },
            "links": [],
            "assets": {},
            "stac_extensions": [
            "https://stac-extensions.github.io/processing/v1.1.0/schema.json"
            ],
            "collection": "my-collection"
         }
      ]
   }

CLI Usage
---------

To run a Task as a CLI application, add a main definition to the class inheriting Task:

.. code-block:: python

   if __name__ == "__main__":
      MyTask.cli()

This provides a CLI that supports several useful flags for using stac-task. Invoking it
without any arguments will print usage.

A common way of invoking the task is:

.. code-block:: console

   src/mytask/mytask.py run --local --logging DEBUG


An example of running it might look like:

.. code-block:: console

   src/mytask/mytask.py run --logging DEBUG --local my-input-file.json

Payload can be read from stdin:

.. code-block:: console

   cat input.json | src/mytask/mytask.py run > tee output.json

The first argument is the command, of which the only option currently is `run`.

- `--logging <LEVEL>` - configure the logging level of the task, one of DEBUG, INFO, WARN, ERROR, or CRITICAL
- `--local` - sets several other flags to reasonable values for local testing, including `save-workdir`,
   `skip-upload`, `skip-validation`, sets the `workdir`` to the directory `local-output`, and
   sets the `output` file to `local-output/output-payload.json`.
- `input` - the location of the input payload file

All of the parameters set by `--local` can also be configured independently:

- `--workdir <PATH>` - the directory that task operations should use for storage
- `--save-workdir` - retain the workdir after the task exits
- `--output <FILEPATH>` - the file path to write the task output to
- `--skip-upload` - don't upload the payload to S3
- `--skip-validation` - don't perform JSON validate on the payload

API Usage
---------

The Task constructor accepts a `payload` argument of type `dict[str, Any]`, usually passed
though the `handler` static method, that represents
a JSON object. This can either be the payload itself or a reference to the actual payload.
If the Task payload dictionary contains a field named either `href` or `url`, the `handler` method will set
the Task's payload to the contents of that URI. Any fsspec storage supported and configured can be used,
such as a local file, a remote HTTP URL, or an S3 URI.

Typically, this payload contains configuration needed for the Task to execute. The payload can be
accessed via `self._payload`. The Task can directly modify the payload, though most commonly,
the payload is only added to by returning a list of STAC Items from the overridden `process` method.

When the `handler` static method is invoked, the following sequence of events happens:

- the `validate` method is called on the payload
- the payload is populated with either the direct value or the contents of `href` or `url`
- the `process` method is executed to generate a list of STAC Items
- the list of list of STAC Items (represented as list of dictionaries) output from
   `process` is assigned to the payload `features` attribute
   to the payload's `features` attribute
- the payload's property `/process/upload_options/collections` mapping uses
  JSONPath to map attributes of the
  output Item to the collection that should be assigned to it
- the contents of _workdir are deleted, unless `save-workdir` is set
