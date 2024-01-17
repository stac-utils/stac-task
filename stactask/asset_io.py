import asyncio
import logging
import os
from os import path as op
from typing import Any, Dict, Iterable, List, Optional, Union

import fsspec
from boto3utils import s3
from fsspec import AbstractFileSystem
from pystac import Item
from pystac.layout import LayoutTemplate

logger = logging.getLogger(__name__)

# global dictionary of sessions per bucket
s3_client = s3()

SIMULTANEOUS_DOWNLOADS = int(os.getenv("STAC_SIMULTANEOUS_DOWNLOADS", 3))
sem = asyncio.Semaphore(SIMULTANEOUS_DOWNLOADS)


async def download_file(fs: AbstractFileSystem, src: str, dest: str) -> None:
    async with sem:
        logger.debug(f"{src} start")
        if hasattr(fs, "_get_file"):
            await fs._get_file(src, dest)
        elif hasattr(fs, "get_file"):
            fs.get_file(src, dest)
        else:
            raise NotImplementedError(
                "stactask only supports filesystems providing"
                " `get_file` or `_get_file` interface"
            )
        logger.debug(f"{src} completed")


async def download_item_assets(
    item: Item,
    assets: Optional[List[str]] = None,
    save_item: bool = True,
    overwrite: bool = False,
    path_template: str = "${collection}/${id}",
    absolute_path: bool = False,
    keep_original_filenames: bool = False,
    **kwargs: Any,
) -> Item:
    _assets = item.assets.keys() if assets is None else assets

    # determine path from template and item
    layout = LayoutTemplate(path_template)
    path = layout.substitute(item)

    # make necessary directories
    os.makedirs(path, exist_ok=True)

    new_item = item.clone()

    tasks = []
    for a in _assets:
        if a not in item.assets:
            continue
        href = item.assets[a].href

        # local filename
        if keep_original_filenames:
            basename = os.path.basename(href)
        else:
            basename = a + os.path.splitext(href)[1]
        new_href = os.path.join(path, basename)
        if absolute_path:
            new_href = os.path.abspath(new_href)

        # save file
        if not os.path.exists(new_href) or overwrite:
            fs = fsspec.core.url_to_fs(href, asynchronous=True, **kwargs)[0]
            task = asyncio.create_task(download_file(fs, href, new_href))
            tasks.append(task)

        # update
        new_item.assets[a].href = new_href

    await asyncio.gather(*tasks)

    # save Item metadata alongside saved assets
    if save_item:
        new_item.remove_links("root")
        new_item.save_object(dest_href=os.path.join(path, "item.json"))

    return new_item


async def download_items_assets(items: Iterable[Item], **kwargs: Any) -> List[Item]:
    tasks = []
    for item in items:
        tasks.append(asyncio.create_task(download_item_assets(item, **kwargs)))
    new_items: List[Item] = await asyncio.gather(*tasks)
    return new_items


def upload_item_assets_to_s3(
    item: Item,
    assets: Optional[List[str]] = None,
    public_assets: Union[None, List[str], str] = None,
    path_template: str = "${collection}/${id}",
    s3_urls: bool = False,
    headers: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Item:
    """Upload Item assets to s3 bucket
    Args:
        item (Dict): STAC Item
        assets (List[str], optional): List of asset keys to upload. Defaults to None.
        public_assets (List[str], optional): List of assets keys that should be
            public. Defaults to [].
        path_template (str, optional): Path string template. Defaults to
            '${collection}/${id}'.
        s3_urls (bool, optional): Return s3 URLs instead of http URLs. Defaults
            to False.
        headers (Dict, optional): Dictionary of headers to set on uploaded
            assets. Defaults to {},
    Returns:
        Dict: A new STAC Item with uploaded assets pointing to newly uploaded file URLs
    """
    if headers is None:
        headers = {}

    # deepcopy of item
    _item = item.to_dict()

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
