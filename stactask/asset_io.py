import boto3
from copy import deepcopy
import json
import logging
from os import getenv, path as op
import requests
from string import Formatter, Template
from typing import Dict, Optional, List

from boto3utils import s3, secrets
from botocore.exceptions import ClientError
from dateutil.parser import parse as dateparse

logger = logging.getLogger(__name__)

## global dictionary of sessions per bucket
s3_sessions = {}

import asyncio
import os

import fsspec
from pystac.layout import LayoutTemplate

SIMULTANEOUS_DOWNLOADS = 3

sem = asyncio.Semaphore(SIMULTANEOUS_DOWNLOADS)
    
async def download_file(fs, src, dest):
    async with sem:
        print(f"{src} start")
        await fs._get_file(src, dest)
        print(f"{src} completed")

    
async def download_item_assets(item, assets=None, save_item=True, overwrite=False,
                         path_template='${collection}/${id}', absolute_path=False):
    
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
        ext = os.path.splitext(href)[-1]
        new_href = os.path.join(path, a + ext)
        if absolute_path:
            new_href = os.path.abspath(new_href)
        
        # save file
        if not os.path.exists(new_href) or overwrite:
            fs = fsspec.filesystem("http", asynchronous=True)
            tasks.append(asyncio.create_task(download_file(fs, href, new_href)))

        # update
        new_item.assets[a].href = new_href
    
    #async with sem:
    await asyncio.wait(tasks)
    
    # save Item metadata alongside saved assets
    if save_item:
        new_item.remove_links('root')
        new_item.save_object(dest_href=os.path.join(path, 'item.json'))
    
    return new_item


async def download_items_assets(items, max_downloads=3, **kwargs):
    tasks = []
    for item in items:
        tasks.append(asyncio.create_task(download_item_assets(item, **kwargs)))
    new_items = await asyncio.wait(tasks)
    return new_items



# note this file has been copied from https://github.com/cirrus-geo/cirrus-lib/blob/main/src/cirrus/lib/transfer.py
# functionality for supplying relative paths has been removed
# and the get_path function comes from https://github.com/cirrus-geo/cirrus-lib/blob/main/src/cirrus/lib/utils.py

def get_path(item: Dict, template: str='${collection}/${id}') -> str:
    """Get path name based on STAC Item and template string
    Args:
        item (Dict): A STAC Item.
        template (str, optional): Path template using variables referencing Item fields. Defaults to '${collection}/${id}'.
    Returns:
        [str]: A path name
    """
    _template = template.replace(':', '__colon__')
    subs = {}
    for key in [i[1] for i in Formatter().parse(_template.rstrip('/')) if i[1] is not None]:
        # collection
        if key == 'collection':
            subs[key] = item['collection']
        # ID
        elif key == 'id':
            subs[key] = item['id']
        # derived from date
        elif key in ['year', 'month', 'day']:
            dt = dateparse(item['properties']['datetime'])
            vals = {'year': dt.year, 'month': dt.month, 'day': dt.day}
            subs[key] = vals[key]
        # Item property
        else:
            subs[key] = item['properties'][key.replace('__colon__', ':')]
    return Template(_template).substitute(**subs).replace('__colon__', ':')


def get_s3_session(bucket: str=None, s3url: str=None, **kwargs) -> s3:
    """Get boto3-utils s3 class for interacting with an s3 bucket. A secret will be looked for with the name
    `cirrus-creds-<bucket-name>`. If no secret is found the default session will be used
    Args:
        bucket (str, optional): Bucket name to access. Defaults to None.
        url (str, optional): The s3 URL to access. Defaults to None.
    Returns:
        s3: A boto3-utils s3 class
    """
    if s3url:
        parts = s3.urlparse(s3url)
        bucket = parts['bucket']

    if bucket and bucket in s3_sessions:
        return s3_sessions[bucket]
    # otherwise, create new session for this bucket
    creds = deepcopy(kwargs)

    try:
        # get credentials from AWS secret
        secret_name = f"cirrus-creds-{bucket}"
        _creds = secrets.get_secret(secret_name)
        creds.update(_creds)
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            # some other client error we cannot handle
            raise e
        logger.info(f"Secret not found, using default credentials: '{secret_name}'")


    requester_pays = creds.pop('requester_pays', False)
    session = boto3.Session(**creds)
    s3_sessions[bucket] = s3(session, requester_pays=requester_pays)
    return s3_sessions[bucket]


def download_from_http(url: str, path: str='') -> str:
    """ Download a file over http and save to path
    Args:
        url (str): A URL to download
        path (str, optional): A local path name to save file. Defaults to '' (current directory)
    Returns:
        str: Local filename of saved file. Basename is the same as the URL basename
    """
    filename = op.join(path, op.basename(url))
    resp = requests.get(url, stream=True)
    with open(filename, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    return filename


def upload_item_assets(item: Dict, assets: List[str]=None, public_assets: List[str]=[],
                       path_template: str='${collection}/${id}', s3_urls: bool=False,
                       headers: Dict={}, s3_session: s3=None, **kwargs) -> Dict:
    """Upload Item assets to s3 bucket
    Args:
        item (Dict): STAC Item
        assets (List[str], optional): List of asset keys to upload. Defaults to None.
        public_assets (List[str], optional): List of assets keys that should be public. Defaults to [].
        path_template (str, optional): Path string template. Defaults to '${collection}/${id}'.
        s3_urls (bool, optional): Return s3 URLs instead of http URLs. Defaults to False.
        headers (Dict, optional): Dictionary of headers to set on uploaded assets. Defaults to {}.
        s3_session (s3, optional): boto3-utils s3 object for s3 interactions. Defaults to None
    Returns:
        Dict: A new STAC Item with uploaded assets pointing to newly uploaded file URLs
    """
    # if assets not provided, upload all assets
    _assets = assets if assets is not None else item['assets'].keys()

    # determine which assets should be public
    if type(public_assets) is str and public_assets == 'ALL':
        public_assets = item['assets'].keys()

    # deepcopy of item
    _item = deepcopy(item)

    for key in [a for a in _assets if a in item['assets'].keys()]:
        asset = item['assets'][key]
        filename = asset['href']
        if not op.exists(filename):
            logger.warning(f"Cannot upload {filename}: does not exist")
            continue
        public = True if key in public_assets else False
        _headers = {}
        if 'type' in asset:
            _headers['ContentType'] = asset['type']
        _headers.update(headers)
        # output URL
        url = get_path(item, op.join(path_template, op.basename(filename)))
        parts = s3.urlparse(url)
        s3_session = get_s3_session(parts['bucket'])

        # upload
        logger.debug(f"Uploading {filename} to {url}")
        url_out = s3_session.upload(filename, url, public=public, extra=_headers, http_url=not s3_urls)
        _item['assets'][key]['href'] = url_out
    return _item