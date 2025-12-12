Usage
=====

.. _installation:
.. _a_simple_task_definition:
.. _cli_usage:
.. _api_usage:

Installation
------------

To use **stac-task**, first install it using pip:

.. code-block:: console

   (.venv) $ pip install stactask


A simple task definition
------------------------

The intended use of **stac-task** is for a developer to extend the ``stactask.Task``
class. A trivial example class that does this is shown below. It accepts a payload
containing a task parameter ``item_id`` and generates a STAC Item with this ID.

.. code-block:: python

   #!/usr/bin/env python

   import logging
   import os
   from datetime import datetime, timezone
   from typing import Any

   from pystac import Item
   from stactask.exceptions import InvalidInput
   from stactask.task import Task


   class MyTask(Task):
      name = "my-task"
      description = "Create STAC Items for payload"
      version = "v2024.02.01"

      # override from Task
      def validate(self) -> bool:
         if "item_id" not in self.task_options:
            raise InvalidInput("Missing required field 'item_id' in task options")
         return True

      # override from Task
      def process(self, **kwargs: Any) -> list[dict[str, Any]]:
         item = Item(
            id=self.task_options["item_id"],
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

         self.logger.debug(f"Created Item with id '{item.id}'")

         return [item.to_dict()]

   # Support for running as a Lambda Function
   def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
      return MyTask.handler(event)

   # Support for running as a CLI application
   if __name__ == "__main__":
      MyTask.cli()

A possible input payload looks like the following:

.. code-block:: json

   {
      "id": "my-task/workflow-my-task/5427299e5b635537f33c07e0ad32fb87",
      "process": [
         {
            "upload_options": {
               "path_template": "s3://my-bucket/${collection}/${year}/${month}/${day}/${id}"
            },
            "collection_matchers": [
               {
                  "type": "jsonpath",
                  "pattern": "$[?(@.id =~ '.*')]",
                  "collection_name": "my-collection"
               }
            ],
            "tasks": {
               "my-task": {
                  "item_id": "G23923"
               }
            }
         }
      ]
   }

The ``collection_matchers`` array defines how to assign output STAC Items to a
collection. More than one matcher can be defined, and the first one that matches is
used. In this case, we only have one matcher defined that matches on any Item ``id``
value. Collection assignment occurs after the Tasks's ``process`` method is called.

The ``upload_options`` object defines AWS S3 upload options for Item assets In this
case, the only option defined is a ``path_template`` that uses an Item's collection ID,
year, month, day, and ID to construct the S3 key for the Item's assets. Our example Task
does not upload any Item assets to S3, so the ``upload_options`` are not used and could
be an empty object in this case.

Running the example module defined above with ``python my-task.py run in.json`` results
in the following output JSON, which contains the original input payload plus a new
``features`` array containing the Item created by the Task's ``process`` method.

.. code-block:: json

   {
      "id": "my-task/workflow-my-task/5427299e5b635537f33c07e0ad32fb87",
      "process": [
         {
            "collection_matchers": [
               {
                  "type": "jsonpath",
                  "pattern": "$[?(@.id =~ '.*')]",
                  "collection_name": "my-collection"
               }
            ],
            "collection_options": {
               "my-collection": {
                  "upload_options": {
                     "path_template": "{collection}/{year}/{month}/{day}/{item_id}"
                  }
               }
            },
            "tasks": {
               "my-task": {
                  "item_id": "G23923"
               }
            }
         }
      ],
      "features": [
         {
            "type": "Feature",
            "stac_version": "1.1.0",
            "stac_extensions": [],
            "id": "G23923",
            "geometry": {
               "type": "Polygon",
               "coordinates": [
                  [
                     [100.0, 0.0],
                     [101.0, 0.0],
                     [101.0, 1.0],
                     [100.0, 1.0],
                     [100.0, 0.0],
                  ]
               ]
            },
            "bbox": [],
            "properties": {
               "datetime": "2025-09-14T13:40:34.201426Z"
            },
            "links": [],
            "assets": {},
            "collection": "my-collection"
         }
      ]
   }

Note the presence of the ``collection`` field, which was automatically populated based
on the ``collection_matchers`` definition in the input payload.

CLI Usage
---------

To run a Task as a CLI application, add a ``__name__ == "__main__"`` check to the module
containing your Task class:

.. code-block:: python

   if __name__ == "__main__":
      MyTask.cli()

This provides a CLI that supports several useful flags for using **stac-task**. Invoking
it without any arguments will print usage. Note that the first argument of the command
is always ``run``.

A common way of invoking the task with the CLI is:

.. code-block:: console

   src/mytask/mytask.py run --logging DEBUG --local my-input-file.json

where the ``--local`` option provides a set of pre-configured option values, including
a name for the local working directory, the name of the output JSON, whether to
save the working directory, and whether to bypass any Item asset uploading that your
task might perform.

Payloads can also be read from stdin:

.. code-block:: console

   cat my-input-file.json | src/mytask/mytask.py run --logging DEBUG --local

API Usage
---------

The Task constructor accepts a ``payload`` argument of type ``dict[str, Any]``, usually
passed though the ``handler`` class method, that represents a JSON object. This can
either be the payload itself or a reference to the actual payload. If the Task payload
dictionary contains a field named either ``href`` or ``url``, the ``handler`` method
interprets the field to be a reference to the actual payload and will set the Task's
payload to the contents of that URI. Any **fsspec** storage supported and configured can
be used, such as a local file, a remote HTTP URL, or an S3 URI.

Task executions typically requires configuration information contained in the payload,
which can be accessed via ``self.payload``. The Task can directly modify the
``self.payload`` dictionary, though it is more common for the payload to simply be
extended by returning a list of STAC Items from the overridden ``process`` method.

When the ``handler`` class method is invoked, the following sequence of events happens:

- The payload is loaded with either the direct value or the contents of ``href`` or
  ``url``.
- A Task instance is created with this payload and any keyword arguments, which triggers
  built-in payload validation and execution of the (potentially) overridden ``validate``
  method.
- The ``process`` method is executed to generate a list of STAC Items.
- The list of STAC Items (represented as list of dictionaries) output from
  ``process`` is assigned to the payload ``features`` attribute.
- Item collection assignment occurs using either the ``/process/collection_matchers``
  list or the legacy ``/process/upload_options/collections`` dictionary.
- The temporary work directory is deleted, unless ``save-workdir`` is set.
