======================
Cirrus Process payload
======================

A Cirrus process payload defines the inputs for a STAC task or a STAC workflow
(a chain of one or more STAC Tasks) - it provides a portable, JSON-based
configuration that encapsulates both the STAC Items to process and options
needed by ``stac-task``. A payload is a STAC FeatureCollection that (usually)
contains one or more STAC Items and a ``process`` definition that configures
the workflow.

The conceptual thought process behind constructing a payload is this:

1. Identify or define the STAC Item(s) to be processed.
2. Define the workflow:

   - How should the workflow be structured? (*e.g.* single STAC task? series
     of STAC tasks?)
   - What global parameters should be applied to all tasks in the workflow?
   - How should each task be configured? (*i.e.*, what parameters are required
     for each task)?
3. How should Collections be assigned to the output STAC Item(s)?
4. How and where should Items and Item Assets be uploaded?

.. _task-input:

Top-level Payload Fields
========================

A payload is a STAC FeatureCollection and is **required** have the following top-level
fields.

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Field Name
     - Type
     - Description
   * - type
     - string
     - Must be "FeatureCollection"
   * - features
     - [Item]
     - An array of STAC Items
   * - :ref:`process <process-definition>`
     - [ProcessDefinition Object]
     - An array of one :ref:`ProcessDefinition <process-definition>` object

A very basic payload with a single STAC Item and a single global workflow
parameter might look like this:

.. code-block:: json

    {
        "type": "FeatureCollection",
        "features": [
            {"...STAC Item..."}
        ],
        "process": [
            {
                "description": "Example process definition",
                "workflow_options": {
                    "global_param": "foo"
                },
            }
        ]
    }

.. _process-definition:

ProcessDefinition Object
========================

The ``process`` block (array) must include a *single* ``ProcessDefinition``
object that provides the configuration options for a Task or a workflow of
Tasks. Each Task in the workflow can have its own configuration options, and
there are also global options that apply to all Tasks in the workflow.

The following fields are supported in a ``ProcessDefinition`` object:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field Name
     - Type
     - Description
   * - description
     - string
     - Description of the process configuration
   * - :ref:`workflow_options <workflow-options>`
     - ``Map<string, Any>``
     - Dictionary of configuration options applied to all tasks in a workflow
   * - :ref:`tasks <tasks>`
     - ``Map<string, Map<string, Any>>``
     - Dictionary of task configurations
   * - :ref:`upload_options <upload-options>`
     - ``UploadOptions`` Object
     - An :ref:`UploadOptions <upload-options>` object
   * - :ref:`collection_matchers <collection-matcher>`
     - [``CollectionMatcher`` Object]
     - An array of :ref:`CollectionMatcher <collection-matcher>` objects used
       for collection assignment. Mutually exclusive with
       ``upload_options.collections`` (deprectated).
   * - :ref:`collection_options <collection-options>`
     - ``Map<string, Map<string, Any>>``
     - Dictionary of collection-specific configuration options

.. _workflow-options:

workflow_options
----------------

The ``workflow_options`` field is a dictionary of options that apply to all
tasks in the workflow. ``stac-task`` combines the ``workflow_options``
dictionary with each task's option dictionary (see :ref:`tasks <tasks>`, below).
If a key in the ``workflow_options`` dictionary conflicts with a key in a
task's option dictionary, the task option value takes precedence.

Here is an example of a ``workflow_options`` dictionary with a single global
parameter:

.. code-block:: json

   {
       "workflow_options": {
           "global_param": "global_value"
       }
   }

.. _tasks:

tasks
-----

The ``tasks`` field is a dictionary where each key is a task name (the key must
match the top-level ``name`` property defined for the ``stactask.Task``
object). The value for any task name key is a dictionary that defines a set of
task-specific parameters. ``stac-task`` converts the task parameter dictionary
to a set of keywords that is passed to the Task's ``process`` function either
via the explicitly defined method signature (``args``) or as keyword arguments
(``kwargs``). A task parameter dictionary is optional, but if it exists, the
Task documentation should define each of the required parameters.

Here is an example ``tasks`` dictionary with two tasks, ``task-a`` and ``task-c``:

.. code-block:: json

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

In the example above, a task named ``task-a`` would have the ``param1=value1``
key-value pair passed as a keyword, while ``task-c`` would have
``param2=value2`` passed in. If there were a ``task-b`` to be run, it would not be
passed any keywords.

.. _upload-options:

UploadOptions Object
--------------------

An ``UploadOptions`` object includes parameters that define how Items and Item
Assets should be uploaded to the cloud (note that presently only AWS S3 is
suported).

The following fields are supported in an ``UploadOptions`` object:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field Name
     - Type
     - Description
   * - path_template
     - string
     - **REQUIRED.** A string template for specifying the location of uploaded Assets
   * - public_assets
     - [string]
     - A list of Asset keys that should be marked as public when uploaded
   * - headers
     - Map<string, string>
     - A set of key, value headers to send when uploading data to S3
   * - collections
     - Map<string, string>
     - **DEPRECATED.** A mapping of output Collection name to a JSONPath
       pattern
   * - s3_urls
     - boolean
     - Controls the format of hrefs (URLs) in the output STAC Item(s) - either
       *s3://* if ``true`` or *https://* if false. Defaults to ``false``

Upload options can be defined either globally or by Collection:

   - If the ``process`` block has a top-level ``upload_options`` key, that
     ``UploadOptions`` object will define global upload options.
   - If Collection-specific options are provided (via the ``collection_options``
     key in the ``ProcessDefinition`` object), and those options include an
     ``upload_options`` key, ``stac-task`` will override the global options with
     the Collection-specific options for any Items assigned to that Collection.
     See :ref:`collection-options <collection-options>`, below, for more
     information.

path_template
^^^^^^^^^^^^^

The ``path_template`` string is a way to specify the upload destination for any
Item Assets. The template is processed from a STAC Item using metadata from the
Item itself. The template can contain fixed strings along with variables used
for substitution. See `the PySTAC documentation for LayoutTemplate
<https://pystac.readthedocs.io/en/stable/api/layout.html#pystac.layout.LayoutTemplate>`_
for a list of supported template variables and their meaning.

Example:

.. code-block:: json

   "path_template": "s3://my-bucket/${collection}/${year}/${month}/${day}/${id}"

...so a STAC Item like this:

.. code-block:: json

   {
       "type": "Feature",
       "id": "LC08_044034_20200716",
       "collection": "landsat-c2l2",
       "properties": {
           "datetime": "2020-07-16T10:15:30Z",
           "...other properties..."
       },
       "...other fields..."
   }

...would have its Assets uploaded to this path:
``s3://my-bucket/landsat-c2l2/2020/07/16/LC08_044034_20200716/``

collections
^^^^^^^^^^^

.. warning::
   This field is deprecated in favor of the ``collection_matchers`` array.
   Note that, unlike ``collection_matchers``, the ``collections`` field is
   an unordered dictionary and because order matters when matching,
   **using the** ``collections`` **field may result in incorrect Collection
   assignment.**

The ``collections`` dictionary provides a Collection ID and JSONPath pattern
for matching against STAC Items. Following processing, when Items are returned
from the ``Task.process`` method Items are checked against the patterns in the
``collections`` dictionary and Collection ID is assigned based on JSONPath
pattern matching. Note that the *first* match to be found is used to assign
Collections (if order matters to pattern matching, use ``collection_matchers``
instead).

Example:

.. code-block:: json

   "collections": {
       "landsat-c2l2": "$[?(@.id =~ 'LC08.*')]",
       "sentinel-2-l2a": "$[?(@.id =~ 'S2.*')]"
   }

In this example, the task will set any STAC Items that have an ID beginning
with "LC08" to the ``landsat-c2l2`` Collection and any STAC Items that have an
ID beginning with "S2" to the ``sentinel-2-l2a`` Collection.

s3_urls
^^^^^^^

The ``s3_urls`` boolean sets the format for hrefs (URLs) in the output STAC
Item(s) - this applies to Assets as well as Links. If ``s3_urls`` is set to
``true``, ``stac-task`` will generate S3 URI-formatted hrefs.  For example:

   ``s3://my-bucket/landsat-c2l2/2020/07/16/LC08_044034_20200716/B4.tif``

If ``s3_urls`` is set to ``false`` (default), ``stac-task`` will generate
http-formatted S3 hrefs.  For example:

   ``https://my-bucket.s3.amazonaws.com/landsat-c2l2/2020/07/16/LC08_044034_20200716/B4.tif``

.. _collection-matcher:

CollectionMatcher Object
------------------------

The ``collection_matchers`` array provides the information for ``stac-task`` to
automatically search returned STAC Items and assign a Collection to each one.
Collection assignment works by searching an Item for a JSONPath pattern and, if
that pattern is found, setting the Item's Collection. A "catch_all" object can
be included to assign a Collection to any Item without a match.
``collection_matchers`` are processed in the order they appear in the array,
thus the first match found determines the Collection assignment.

Note that Collection assignment occurs *after* Items have been returned from
the ``Task.process`` method (*i.e.* after user-defined processing is
complete) - consider this when uploading Items to S3 or otherwise writing them
*prior* to returning them. Also note that ``collection_matchers`` are mutually
exclusive with the legacy ``collections`` field in ``UploadOptions``.

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Field Name
     - Type
     - Description
   * - type
     - string
     - **REQUIRED.** The matcher type. Supported values: "jsonpath", "catch_all"
   * - pattern
     - string
     - **CONDITIONAL.** JSONPath pattern for matching Items. Required for all types except "catch_all"
   * - collection_name
     - string
     - **REQUIRED.** The Collection ID to assign to matching Items

Example:

.. code-block:: json

   "collection_matchers": [
       {
           "type": "jsonpath",
           "pattern": "$[?(@.id =~ 'LC08.*')]",
           "collection_name": "landsat-c2l2"
       },
       {
           "type": "jsonpath",
           "pattern": "$[?(@.id =~ 'S2.*')]",
           "collection_name": "sentinel-2-l2a"
       },
       {
           "type": "catch_all",
           "collection_name": "default-collection"
       }
   ]

In this example, Items whose ID begins with "LC08" will be assigned to the
``landsat-c2l2`` Collection, those whose ID begins with "S2" will be assigned
to ``sentinel-2-l2a``, and any remaining Items will be assigned to
``default-collection``.

See `JSONPath Online Evaluator <https://jsonpath.com>`_ to experiment with
JSONPath and `regex101 <https://regex101.com>`_ to experiment with regex.

.. _collection-options:

collection_options
------------------

The ``collection_options`` field is a dictionary that allows you to specify
Collection-specific configuration options, including ``UploadOptions`` objects. For
example, when uploading Asset data to S3, the Task will first look for
Collection-specific upload options and fall back to the global options (the top-level
``upload_options`` dictionary) if none are found.

Example:

.. code-block:: json

   "collection_options": {
       "sentinel-2-l2a": {
           "upload_options": {
               "path_template": "s3://sentinel-bucket/${collection}/${year}/${month}/${day}/${id}",
               "headers": {
                   "StorageClass": "INTELLIGENT_TIERING"
               }
           }
       },
       "landsat-c2l2": {
           "upload_options": {
               "path_template": "s3://landsat-bucket/${collection}/${path}/${row}/${id}",
               "public_assets": ["thumbnail", "overview"]
           }
       }
   }


Full ProcessDefinition Example
==============================

.. code-block:: json

   {
       "description": "My process configuration",
       "upload_options": {
           "path_template": "s3://my-bucket/${collection}/${year}/${month}/${day}/${id}",
           "public_assets": ["thumbnail", "overview"]
       },
       "collection_matchers": [
           {
               "type": "jsonpath",
               "pattern": "$[?(@.id =~ 'LC08.*')]",
               "collection_name": "landsat-c2l2"
           },
           {
               "type": "jsonpath",
               "pattern": "$[?(@.id =~ 'S2.*')]",
               "collection_name": "sentinel-2-l2a"
           },
           {
               "type": "catch_all",
               "collection_name": "default-collection"
           }
       ],
       "collection_options": {
           "sentinel-2-l2a": {
               "upload_options": {
                   "path_template": "s3://sentinel-bucket/${collection}/${mgrs:utm_zone}/${mgrs:latitude_band}/${mgrs:grid_square}/${year}/${month}/${id}",
                   "headers": {
                       "StorageClass": "INTELLIGENT_TIERING"
                   }
               }
           }
       },
       "tasks": {
           "task-name": {
               "param": "value"
           }
       },
       "workflow_options": {
           "global_param": "global_value"
       }
   }
