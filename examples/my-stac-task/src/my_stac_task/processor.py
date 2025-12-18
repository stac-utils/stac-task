from datetime import datetime

import pystac
from stactask import Payload


def process_item(payload: Payload) -> Payload:
    """Create and minimally process a STAC Item.

    Parameters
    ----------
    payload : Payload
        The Cirrus process payload. ``Payload`` is a dict-like object that provides
        convenient accessors for commonly used payload properties. The following
        properties are available on the payload:

        - ``process_definition`` : dict
            The first element of the payload's ``process`` list. Contains the
            task configuration and workflow options.
        - ``workflow_options`` : dict
            Workflow-level options extracted from ``process_definition``.
        - ``task_options_dict`` : dict[str, dict]
            Mapping of task names to their parameter dictionaries.
        - ``upload_options`` : dict
            Upload-related options (for example, path templates and headers).
        - ``items_as_dicts`` : list[dict]
            The list of feature dictionaries (STAC Items) present in the payload.
        - ``collection_matchers`` : list[dict]
            A list of matcher objects used to map items to collections.
        - ``collection_options`` : dict[str, dict]
            Per-collection options used to override default behaviour.

        For additional definitions, see the stac-task README:
        https://github.com/stac-utils/stac-task?tab=readme-ov-file#stac-task-stac-task
        ...or the Cirrus docs:
        https://cirrus-geo.github.io/cirrus-geo/v1.2.0/cirrus/30_payload.html

    Returns
    -------
    Payload
        The modified payload containing the newly created STAC Item in the
        ``features`` list.
    """

    # create an item
    item = pystac.Item(
        id="example-item",
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [-71.4667693618289, 43.3262376051166],
                    [-71.4278035338514, 42.3392708844627],
                    [-70.6447744862405, 42.3532726633038],
                    [-70.2637344878527, 43.3458642540582],
                    [-71.4667693618289, 43.3262376051166],
                ]
            ],
        },
        bbox=[-71.466769, 42.339271, -70.263734, 43.345864],
        datetime=datetime(2025, 3, 4, 15, 41, 14),
        properties={"example-property": "value"},
    )

    # add an asset
    item.add_asset(
        "example_asset",
        pystac.Asset(
            title="Example",
            href="http://example.com/example_asset.tif",
            media_type="image/tiff",
        ),
    )

    # add the Item to the payload features list
    if payload.get("features") is None:
        payload["features"] = []
    payload.get("features").append(item.to_dict())

    return payload
