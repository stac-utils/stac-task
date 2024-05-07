import asyncio
import logging
from os import path as op
from typing import Any, Iterable, Optional, Union

import stac_asset
from boto3utils import s3
from pystac import Item
from pystac.layout import LayoutTemplate

from .config import DownloadConfig

logger = logging.getLogger(__name__)

# global dictionary of sessions per bucket
global_s3_client = s3()


async def download_item_assets(
    item: Item,
    path_template: str = "${collection}/${id}",
    config: Optional[DownloadConfig] = None,
    keep_non_downloaded: bool = True,
) -> Item:
    return await stac_asset.download_item(
        item=item.clone(),
        directory=LayoutTemplate(path_template).substitute(item),
        file_name="item.json",
        config=config,
        keep_non_downloaded=keep_non_downloaded,
    )


async def download_items_assets(
    items: Iterable[Item],
    path_template: str = "${collection}/${id}",
    config: Optional[DownloadConfig] = None,
    keep_non_downloaded: bool = True,
) -> list[Item]:
    return await asyncio.gather(
        *[
            asyncio.create_task(
                download_item_assets(
                    item=item,
                    path_template=path_template,
                    config=config,
                    keep_non_downloaded=keep_non_downloaded,
                )
            )
            for item in items
        ]
    )


def upload_item_assets_to_s3(
    item: Item,
    assets: Optional[list[str]] = None,
    public_assets: Union[None, list[str], str] = None,
    path_template: str = "${collection}/${id}",
    s3_urls: bool = False,
    headers: Optional[dict[str, Any]] = None,
    s3_client: Optional[s3] = None,
    **kwargs: Any,  # unused, but retain to permit unused attributes from upload_options
) -> Item:
    """Upload Item assets to an S3 bucket
    Args:
        item (Item): STAC Item
        assets (list[str], optional): List of asset keys to upload. Defaults to None.
        public_assets (list[str], optional): List of assets keys that should be
            public. Defaults to [].
        path_template (str, optional): Path string template. Defaults to
            '${collection}/${id}'.
        s3_urls (bool, optional): Return s3 URLs instead of http URLs. Defaults
            to False.
        headers (dict, optional): Dictionary of headers to set on uploaded
            assets. Defaults to {}.
        s3_client (boto3utils.s3, optional): Use this s3 object instead of the default
            global one. Defaults to None.
    Returns:
        Item: A new STAC Item with uploaded assets pointing to newly uploaded file URLs
    """

    if s3_client is None:
        s3_client = global_s3_client

    if headers is None:
        headers = {}

    # deepcopy of item
    _item = item.to_dict(transform_hrefs=False)

    if public_assets is None:
        public_assets = []
    # determine which assets should be public
    elif isinstance(public_assets, str):
        if public_assets == "ALL":
            public_assets = list(_item["assets"].keys())
        else:
            raise ValueError(f"unexpected value for `public_assets`: {public_assets}")

    # if assets not provided, upload all assets
    _assets = assets if assets is not None else _item["assets"].keys()

    for key in [a for a in _assets if a in _item["assets"].keys()]:
        asset = _item["assets"][key]
        filename = asset["href"]
        if not op.exists(filename):
            logger.warning(f"Cannot upload {filename}: does not exist")
            continue
        public = True if key in public_assets else False
        _headers = {}
        if "type" in asset:
            _headers["ContentType"] = asset["type"]
        _headers.update(headers)
        # output URL
        layout = LayoutTemplate(op.join(path_template, op.basename(filename)))
        url = layout.substitute(item)

        # upload
        logger.debug(f"Uploading {filename} to {url}")
        url_out = s3_client.upload(
            filename, url, public=public, extra=_headers, http_url=not s3_urls
        )
        _item["assets"][key]["href"] = url_out

    return Item.from_dict(_item)
