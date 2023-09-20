"""Basic models, with little to no logic.

If models are more complicated, they should go in their own module (aka file).
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

import pystac
import pystac.utils
from pydantic import BaseModel, ConfigDict


class Anything(BaseModel):
    """A model for any dictionary."""

    model_config = ConfigDict(extra="allow")


class UploadOptions(BaseModel):
    """Options for uploading items and assets after payload execution."""

    path_template: str = r"${collection}"
    """A string template for specifying the location of uploaded assets.
    
    See
    https://pystac.readthedocs.io/en/stable/api/layout.html#pystac.layout.LayoutTemplate
    for the available fields.
    """

    headers: Optional[Dict[str, str]] = None
    """A set of key, value headers to send when uploading data to s3"""

    collections: Optional[Dict[str, str]] = None
    """A mapping of output collection name to a JSONPath pattern (for matching Items)"""

    s3_urls: bool = False
    """Controls if the final published URLs should be an s3 or https URL"""


class Process(BaseModel):
    """A process definition"""

    description: Optional[str] = None
    """Description of the process configuration"""

    upload_options: UploadOptions = UploadOptions()
    """Options used when uploading assets to a remote server"""

    tasks: Dict[str, Dict[str, Any]] = {}
    """Dictionary of task configurations"""


class Href(BaseModel):
    """A model for a single href."""

    href: str
    """The href"""


class Properties(BaseModel):
    """The properties of a STAC item."""

    model_config = ConfigDict(extra="allow")

    datetime: Optional[str]
    """The searchable date and time of the assets, which must be in UTC.
    
    It is formatted according to [RFC 3339, section
    5.6](https://tools.ietf.org/html/rfc3339#section-5.6). `null` is allowed,
    but requires `start_datetime` and `end_datetime` from [common
    metadata](common-metadata.md#date-and-time-range) to be set.
    """


class Link(BaseModel):
    """This object describes a relationship with another entity.

    Data providers are advised to be liberal with the links section, to describe
    things like the Catalog an Item is in, related Items, parent or child Items
    (modeled in different ways, like an 'acquisition' or derived data).  It is
    allowed to add additional fields such as a `title` and `type`.
    """

    model_config = ConfigDict(extra="allow")

    href: str
    """The actual link in the format of an URL.
    
    Relative and absolute links are both allowed.
    """

    rel: str
    """Relationship between the current document and the linked document."""

    type: Optional[str] = None
    """[Media
    type](https://raw.githubusercontent.com/radiantearth/stac-spec/master/catalog-spec/catalog-spec.md#media-types)
    of the referenced entity."""

    title: Optional[str] = None
    """A human readable title to be used in rendered displays of the link."""


class Asset(BaseModel):
    """An Asset is an object that contains a URI to data associated with the
    Item that can be downloaded or streamed.

    It is allowed to add additional fields."""

    model_config = ConfigDict(extra="allow")

    href: str
    """URI to the asset object.
    
    Relative and absolute URI are both allowed.
    """

    title: Optional[str] = None
    """The displayed title for clients and users."""

    description: Optional[str] = None
    """A description of the Asset providing additional details, such as how it
    was processed or created.
    
    [CommonMark 0.29](http://commonmark.org/) syntax MAY be used for rich text
    representation.
    """

    type: Optional[str] = None
    """[Media type](#asset-media-type) of the asset."""

    roles: Optional[List[str]] = None
    """The semantic roles of the asset, similar to the use of `rel` in links."""


class Item(BaseModel):
    """A STAC Item.

    We choose to define our own instead of using *stac-pydantic*.
    """

    model_config = ConfigDict(extra="allow")

    type: Literal["Feature"] = "Feature"
    """Type of the GeoJSON Object.
    
    MUST be set to `Feature`.
    """

    stac_version: str = "1.0.0"
    """The STAC version the Item implements."""

    stac_extensions: Optional[List[str]] = None
    """A list of extensions the Item implements."""

    id: str
    """Provider identifier.
    
    The ID should be unique within the Collection that contains the Item."""

    geometry: Optional[Anything] = None
    """Defines the full footprint of the asset represented by this item,
    formatted according to [RFC 7946, section
    3.1](https://tools.ietf.org/html/rfc7946#section-3.1).
    
    The footprint should be the default GeoJSON geometry, though additional
    geometries can be included. Coordinates are specified in Longitude/Latitude
    or Longitude/Latitude/Elevation based on [WGS
    84](http://www.opengis.net/def/crs/OGC/1.3/CRS84).
    """

    bbox: Optional[List[float]] = None
    """Bounding Box of the asset represented by this Item, formatted according
    to [RFC 7946, section 5](https://tools.ietf.org/html/rfc7946#section-5)."""

    properties: Properties = Properties(datetime=None)
    """A dictionary of additional metadata for the Item."""

    links: List[Link] = []
    """List of link objects to resources and related URLs.

    A link with the `rel` set to `self` is strongly recommended.
    """

    assets: Dict[str, Asset] = {}
    """Dictionary of asset objects that can be downloaded, each with a unique key."""

    collection: Optional[str] = None
    """The `id` of the STAC Collection this Item references to.

    This field is *required* if such a relation type is present and is *not
    allowed* otherwise. This field provides an easy way for a user to search for
    any Items that belong in a specified Collection. Must be a non-empty string.
    """

    def to_pystac(self) -> pystac.Item:
        """Converts this pydantic model to a pystac Item.

        Returns:
            pystac.Item: The pystac item.
        """
        return pystac.Item.from_dict(self.model_dump())

    @classmethod
    def from_pystac(cls, item: pystac.Item) -> Item:
        """Converts this pydantic model to a pystac Item.

        Args:
            item: The pystac item

        Returns:
            Item: A pydantic item
        """
        return Item.model_validate(item.to_dict(transform_hrefs=False))
