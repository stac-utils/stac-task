stactask.Task — instance reference
=================================

This file lists the most important attributes, properties, and methods
available on a Task instance (what you can access via self) with concise
definitions.

This documentation is provided to make the user aware of stac-task's features. To learn
more see ``src/stactask/task.py``.

.. _instance_attributes:
.. _properties:
.. _instance_methods:

Instance attributes
-------------------

* **payload (Payload)**: The validated Cirrus process payload wrapped in the
  Payload helper class. Primary access point for process, workflow, task, upload
  options, and features.
* **logger (TaskLoggerAdapter)**: Pre-configured logger that includes task
  metadata (task name/version) and can be used for task logging.
* **s3 (boto3utils.s3)**: If present, convenience S3 client utility for
  reading/writing S3 objects (used by convenience helpers).

Properties
----------------------------------------------------

Properties can be accessed via ``self.<name>``

* **process_definition (dict)**: Convenience accessor for the first element of
  the payload ``process`` list (top-level process configuration for this run).
* **workflow_options (dict)**: Workflow-level options from the process
  definition (global parameters for the workflow).
* **task_options (dict)**: Options for this task: the mapping located at
  ``process.tasks[self.name]`` if present, otherwise an empty dict.
* **parameters (dict)**: Merged parameters, typically ``workflow_options`` merged
  with ``task_options`` (task-level overrides workflow-level).
* **upload_options (dict)**: Upload-related options from the process definition
  (path templates, headers, collections).
* **collection_matchers (list[dict])**: List of collection-matcher definitions
  (JSONPath-based rules used to assign collection names to items).
* **items_as_dicts (list[dict])**: The features list from the payload (each
  element is a STAC Item as a plain dict).
* **items (pystac.ItemCollection)**: A pystac.ItemCollection built from the
  payload features for convenience when working with pystac Item objects.

Instance methods
----------------

* **assign_collections**: Assign collection names to items in the payload using
  ``collection_matchers`` mapping.
* **download_item_assets**: Convenience wrapper to download assets for
  a single Item. Given a pystac.Item, the Task will download each asset's file to its
  local work directory and will update each asset's href.
* **download_items_assets**: Batch variant of ``download_item_assets`` that downloads
  assets for multiple items concurrently (uses asyncio under the hood).
* **upload_item_assets_to_s3**: Upload local assets referenced by an Item to S3
  (based on path templates) and update asset hrefs to their uploaded
  locations. This is an S3-specific helper retained for compatibility.
* **upload_local_item_assets_to_s3**: Helper to find assets whose hrefs point to the
  local workdir and upload only those to S3 (based on path templates), updating hrefs.
* **upload_item_to_s3**: Upload a single Item JSON to S3 (based on path templates) as a
  JSON file.
