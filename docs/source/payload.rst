=================
STAC Task Payload
=================

A STAC task payload defines the inputs for a STAC task or a STAC workflow
(a chain of one or more STAC Tasks) - it provides a portable, JSON-based
configuration that encapsulates both the STAC Items to process and options
needed by ``stac-task``. A payload is a STAC FeatureCollection that (usually)
contains one or more STAC Items and a ``process`` definition that configures
the task(s).

The conceptual thought process behind constructing a payload is this:

1. Identify or define the STAC Item(s) to be processed.
2. Configure the STAC task(s): What parameters are required for each task?
   (And, are there any global parameters that should apply to all tasks?)
3. Which Collection(s) should be assigned to the output STAC Item(s) and how?
4. Where should Items and Item Assets be uploaded?

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
     - An array of zero or more STAC Items
   * - :ref:`process <process-definition>`
     - [ProcessDefinition | ProcessDefinition]
     - An array of one or more :ref:`ProcessDefinition <process-definition>` objects

A very basic payload with a single STAC Item and a single global parameter
might look like this:

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
object containing the configuration options for a Task or a set of Tasks. Each
Task can have its own configuration options, and there are also global options
that apply to all Tasks.

Note that while the ``process`` array *can* include multiple
``ProcessDefinition`` objects, ``stac-task`` reads only the first
``ProcessDefinition`` in the ``process`` array. **\***

The following fields are supported in a ``ProcessDefinition`` object:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field Name
     - Type
     - Description
   * - description
     - ``string``
     - Description of the process configuration
   * - :ref:`tasks <tasks>`
     - ``Map<string, Map<string, Any>>``
     - Dictionary of task configurations
   * - :ref:`workflow_options <workflow-options>`
     - ``Map<string, Any>``
     - Dictionary of configuration options applied to all tasks
   * - :ref:`upload_options <upload-options>`
     - ``UploadOptions`` Object
     - An :ref:`UploadOptions <upload-options>` object
   * - :ref:`collection_matchers <collection-matcher>`
     - ``[CollectionMatcher]``
     - An array of :ref:`CollectionMatcher <collection-matcher>` objects used
       for collection assignment.
   * - :ref:`collection_options <collection-options>`
     - ``Map<string, Map<string, Any>>``
     - Dictionary of collection-specific configuration options

.. admonition:: :sup:`*` Why is ``process`` an array?

    Workflow orchestration systems (like `Cirrus <https://cirrus-geo.github.io/cirrus-geo/v0.15.4/index.html>`_)
    support *chained workflows* where the output of one workflow becomes the
    input to another workflow. In this case, a payload would be reconstructed
    with the second workflow's ``ProcessDefinition`` as the primary (*i.e.*
    first) object in the ``process`` array.

    For more information on chained workflows, see the `Cirrus documentation
    <https://cirrus-geo.github.io/cirrus-geo/v0.15.4/cirrus/components/workflows/chaining.html>`_.

    When defining a simple (non-chained) workflow for use with ``stac-task``,
    only a single ``ProcessDefinition`` object is needed and only the first
    object in the ``process`` array will be read.

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

In the example above, a task named ``task-a`` would have the ``param1='value1'``
key-value pair passed as a keyword, while ``task-c`` would have
``param2='value2'`` passed in. If there were a ``task-b`` to be run, it would
not be passed any keywords.

.. _workflow-options:

workflow_options
----------------

The ``workflow_options`` field is a dictionary of options that apply to *all*
tasks in the workflow. ``stac-task`` combines the ``workflow_options``
dictionary with each task's option dictionary (see :ref:`tasks <tasks>`, above).
If a key in the ``workflow_options`` dictionary conflicts with a key in a
task's option dictionary, the task option value takes precedence.

Here is an example of a ``workflow_options`` dictionary with a single global
parameter that shows how ``workflow_options`` interacts with task-specific
parameter values:

.. code-block:: json

   {
       "workflow_options": {
           "param1": "global_value"
        },
       "tasks": {
           "task-a": {
               "param1": "value1"
           },
           "task-c": {
               "param2": "value2"
           }
       }
   }

In this case, ``task-a`` would get one keyword argument ``param1='value1'``
(overriding the global value for ``param1``), while ``task-c`` would get two:
``param1='global_value'`` and ``param2='value2'``. If another task ``task-b``
also runs, it would get one keyword argument ``param1='global_value'``.

.. _upload-options:

UploadOptions Object
--------------------

An ``UploadOptions`` object includes parameters that define how Items and Item
Assets should be uploaded to the cloud. **+**

The following fields are supported in an ``UploadOptions`` object:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field Name
     - Type
     - Description
   * - path_template
     - ``string``
     - **REQUIRED.** A string template for specifying the location of uploaded Assets
   * - public_assets
     - ``[string]``
     - A list of Asset keys that should be marked as public when uploaded
   * - headers
     - ``Map<string, string>``
     - A set of key, value headers to send when uploading data
   * - s3_urls
     - ``boolean``
     - Controls the format of hrefs (URLs) in the output STAC Item(s) - either
       *s3://* if ``true`` or *https://* if false. Defaults to ``false``

.. admonition:: :sup:`+` Support for cloud storage

    While access to non-AWS cloud storage is possible, `stac-task`, and thus
    also the ``UploadOptions`` object, is tightly coupled to AWS S3 for Item
    and Asset upload operations. Uploading to other cloud providers would
    require custom clients and methods as well as any supporting task
    parameters in the payload.

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

The following fields are supported in a ``CollectionMatcher`` object:

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

.. admonition:: When to assign Collections

    `stac-task` runs *automated* collection assignment *after* Items have been
    returned from the ``Task.process`` method (*i.e.* after user-defined
    processing is complete).  This is convenient if you are not uploading any
    Items or Assets or Collection is not needed to successfully upload (*e.g.*
    your Asset storage does not include Collection in the path).

    There may be cases where you need to assign collections *before* returning
    Items - the primary example is when you are uploading and using Collection
    variables in a ``path_template``. In these cases, you may need to call
    collection assignment explicitly from the ``process`` method (via
    ``self.assign_collections()``) prior to calling upload methods.

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

.. _full-process-definition-example:

Full ProcessDefinition Example
------------------------------

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

.. _stac-task-payload-examples:

STAC Task Payload Examples
===========================

As we have seen, the STAC task payload is a flexible data structure and thus
can accommodate many use cases. This section includes some examples of common
payload configurations.

.. _image-ingest-zero-stac-item-payload:

Image Ingest - Zero STAC Item Payload
------------------

In this example, the payload is intended to run a single STAC task called
``image-ingest``. Since there is no pre-existing Item for the new image, the
payload is constructed with no STAC Items in the ``features`` array. The
necessary parameters for ingesting the image are provided as task parameters in
the ``tasks`` dictionary.

.. code-block:: json

    {
        "type": "FeatureCollection",
        "features": [],
        "process": [
            {
                "upload_options": {
                    "path_template": "s3://image-bucket/${collection}/${year}/${month}/${day}/${id}",
                    "s3_urls": true
                },
                "tasks": {
                    "image-ingest": {
                        "delivery_path": "s3://incoming-data/order-123/image-file.tif",
                        "order_id": "order-123",
                        "collection": "images"
                    }
                }
            }
        ]
    }

In this example, in addition to handling any image processing logic, the
``image-ingest`` task would create a new STAC Item based on the provided
parameters. The variables in the ``path_template`` would be populated from the
new STAC Item's properties. The output of the task would be a payload including
the new STAC Item. There are no other task options defined in this payload.

.. _cog-generation-single-stac-item-payload:

COG Generation - Single STAC Item Payload
------------------

This example is intended to run a single STAC task called ``cog-generation`` on an
existing STAC Item. The payload includes the STAC Item in the ``features`` array
and provides the necessary parameters to generate a cloud-optimized GeoTIFF
(COG) via the ``tasks`` dictionary.

.. code-block:: json

    {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "stac_version": "1.1.0",
                "id": "image-123",
                "geometry": {
                    "...geometry object..."
                },
                "bbox": [
                    "...bounding box items..."
                ],
                "properties": {
                    "datetime": "2025-12-15T12:30:15Z",
                    "other properties..."
                },
                "links": [
                    {
                        "rel": "self",
                        "href": "s3://image-bucket/images/2025/12/15/image-123-stac.json",
                        "type": "application/geo+json"
                    }
                ],
                "assets": {
                    "tif": {
                        "href": "s3://image-bucket/images/2025/12/15/image-123.tif",
                        "type": "image/tiff; application=geotiff",
                        "title": "TIFF image",
                        "roles": [
                            "data"
                        ]
                    },
                    "thumbnail": {
                        "href": "s3://image-bucket/images/2025/12/15/image-123-thumb.jpg",
                        "type": "image/jpeg",
                        "title": "Thumbnail image",
                        "roles": [
                            "preview"
                        ]
                    },
                },
                "collection": "images"
            }
        ],
        "process": [
            {
                "tasks": {
                    "cog-generation": {
                        "asset-key": "tif",
                        "compression": "deflate",
                        "overview_levels": [2, 4, 8, 16]
                    }
                }
            }
        ]
    }

The ``cog-generation`` task would read the provided STAC Item, generate a
COG from the specified Asset (based on the ``asset-key`` parameter), and create
a new Asset in the output STAC Item. The output payload would include the
updated STAC Item with the new COG Asset.

.. _calculate-ndvi-multi-task-workflow:

Calculate NDVI - Multi-task workflow
------------------

This payload example demonstrates a multi-task workflow to calculate the
Normalized Difference Vegetation Index (NDVI) from raw image data. The workflow
includes three tasks: asset fetching, atmospheric correction, and NDVI
generation. The payload includes a single STAC Item representing the raw image
data to be processed.

.. code-block:: json

    {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "stac_version": "1.1.0",
                "id": "image-1234",
                "geometry": {
                    "...geometry object..."
                },
                "bbox": [
                    "...bounding box items..."
                ],
                "properties": {
                    "datetime": "2026-01-05T10:30:00Z",
                    "other properties..."
                },
                "links": [
                    {
                        "rel": "self",
                        "href": "s3://vendor-bucket/2026/01/05/image-1234-stac.json",
                        "type": "application/geo+json"
                    }
                ],
                "assets": {
                    "red": {
                        "href": "s3://vendor-bucket/2026/01/05/image-1234.red.tif",
                        "type": "image/tiff; application=geotiff",
                        "title": "TIFF image",
                        "roles": [
                            "data"
                        ]
                    },
                    "nir": {
                        "href": "s3://vendor-bucket/2026/01/05/image-1234.nir.tif",
                        "type": "image/tiff; application=geotiff",
                        "title": "TIFF image",
                        "roles": [
                            "data"
                        ]
                    },
                    "...additional assets..."
                },
                "collection": "vendor-images"
            }
        ],
        "process": [
            {
                "workflow_options": {
                    "asset_keys": ["red", "nir"],
                },
                "tasks": {
                    "asset-fetcher": {
                        "download_assets": true,
                        "output_collection": "raw_images"
                    },
                    "atmospheric-correction": {
                        "algorithm": "atmo-fixer",
                        "version": "0.0.1",
                        "dem_path": "s3://dem-bucket/dem-5678.tif",
                        "resampling": "bilinear",
                        "output_collection": "processed-cogs"
                    },
                    "ndvi-generator": {
                        "output_collection": "ndvi"
                    }
                },
                "upload_options": {
                    "path_template": "s3://image-bucket/${collection}/${year}/${month}/${day}/${id}",
                }
            }
        ]
    }

The payload configures 3 separate STAC tasks: the `asset-fetcher` task
downloads the specified Assets, the `atmospheric-correction` task applies
AtmoFixer correction using a provided DEM, and the `ndvi-generator` task
calculates NDVI. Each task specifies an output Collection for the resulting STAC
Items. The global ``asset_keys`` parameter ensures that only the red and NIR
bands are processed by each task. The final output STAC Items and
Assets are uploaded by each task to the specified S3 path via the
``upload_options``.
