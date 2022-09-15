from abc import ABC, abstractmethod
import argparse
from copy import deepcopy
import json
import logging
from os import makedirs
from pathlib import Path
from shutil import rmtree
import sys
from tempfile import mkdtemp
from typing import Dict, List, Optional, Union
from xmlrpc.client import Boolean

from boto3utils import s3
from jsonpath_ng.ext import parser

from .asset_io import download_item_assets, upload_item_assets

# types
PathLike = Union[str, Path]


'''
Tasks can use parameters provided in a `process` Dictionary that is supplied in the ItemCollection
JSON under the "process" field. An example process definition:

```
{
    "description": "My process configuration"
    "upload_options": {
        "path_template": "s3://my-bucket/${collection}/${year}/${month}/${day}/${id}",
        "collections": {
            "landsat-c2l2": ""
        }
    },
    "tasks": {
        "task-name": {
            "param": "value"
        }
    }
}
```
'''


def stac_jsonpath_match(item: Dict, expr: str) -> Boolean:
    """Match jsonpath expression against STAC JSON.
       Use https://jsonpath.herokuapp.com/ to experiment with JSONpath
        and https://regex101.com/ to experiment with regex

    Args:
        item (Dict): A STAC Item
        expr (str): A valid JSONPath expression

    Raises:
        err: Invalid inputs

    Returns:
        Boolean: Returns True if the jsonpath expression matches the STAC Item JSON
    """
    result = [x.value for x in parser.parse(expr).find([item])]
    if len(result) == 1:
        return True
    else:
        return False


class Task(ABC):

    name = 'task'
    description = 'A task for doing things'
    version = '0.1.0'

    def __init__(self: "Task", item_collection: Dict,
                 workdir: Optional[PathLike]=None,
                 skip_validation: Optional[bool] = False,
                 skip_upload: Optional[bool] = False):

        if not skip_validation:
            self.validate(item_collection)

        self._item_collection = item_collection

        # set up logger
        self.logger = logging.getLogger(self.name)

        # skip uploading returned STAC Items and assets 
        self._skip_upload = skip_upload

        # save any output options to be passed to

        # create temporary work directory if workdir is None
        self._workdir = workdir
        if workdir is None:
            self._workdir = Path(mkdtemp())
            self._tmpworkdir = True
        else:
            self._workdir = Path(workdir)
            self._tmpworkdir = False
            makedirs(self._workdir, exist_ok=True)

    def __del__(self):
        # remove work directory if not running locally
        if self._tmpworkdir:
            self.logger.debug(f"Removing work directory {self._workdir}")
            rmtree(self._workdir)

    @property
    def process_definition(self) -> Dict:
        return self._item_collection.get('process', {})

    @property
    def parameters(self) -> Dict:
        return self.process_definition.get('tasks', {}).get(self.name, {})

    @property
    def upload_options(self) -> Dict:
        return self.process_definition.get('upload_options', {})

    @property
    def items(self) -> List[Dict]:
        return self._item_collection['features']

    @classmethod
    def validate(cls, payload) -> bool:
        # put validation logic on input Items and process definition here
        return True

    @classmethod
    def add_software_version(cls, items):
        processing_ext = 'https://stac-extensions.github.io/processing/v1.1.0/schema.json'
        for i in items:
            i['stac_extensions'].append(processing_ext)
            i['stac_extensions'] = list(set(i['stac_extensions']))
            i['properties']['processing:software'] = {
                cls.name: cls.version
            }
        return items

    def assign_collections(self):
        """Assigns new collection names based on
        """
        for i in self.items:
            for col, expr in self.upload_options.get('collections').items():
                if stac_jsonpath_match(i, expr):
                    i['collection'] = col

    def download_item_assets(self, item: Dict, assets: Optional[List[str]]=None):
        """Download provided asset keys for all items in payload. Assets are saved in workdir in a
           directory named by the Item ID, and the items are updated with the new asset hrefs.

        Args:
            assets (Optional[List[str]], optional): List of asset keys to download. Defaults to all assets.
        """
        outdir = self._workdir / Path(item['id'])
        makedirs(outdir, exist_ok=True)
        item = download_item_assets(item, path=outdir, assets=assets)
        return item

    def upload_item_assets(self, item: Dict, assets: Optional[List[str]]=None):
        if self._skip_upload:
            self.logger.warn('Skipping upload of new and modified assets')
            return item
        item = upload_item_assets(item, assets=assets, **self.upload_options)
        return item

    # this should be in PySTAC
    @staticmethod
    def create_item_from_item(item):
        new_item = deepcopy(item)
        # create a derived output item
        links = [l['href'] for l in item['links'] if l['rel'] == 'self']
        if len(links) == 1:
            # add derived from link
            item['links'].append({
                'title': 'Source STAC Item',
                'rel': 'derived_from',
                'href': links[0],
                'type': 'application/json'
            })
        return item

    @abstractmethod
    def process(self, **kwargs) -> List[Dict]:
        """Main task logic - virtual

        Returns:
            [type]: [description]
        """
        # download assets of interest, this will update self.items
        #self.download_assets(['key1', 'key2'])
        # do some stuff
        #self.upload_assets(['key1', 'key2'])
        return self.items

    @classmethod
    def handler(cls, payload, **kwargs):
        task = cls(payload, **kwargs)
        try:
            items = task.process(**task.parameters)
            task._item_collection['features'] = cls.add_software_version(items)
            task.assign_collections()
            with open(task._workdir / "stac.json", "w") as f:
                f.write(json.dumps(task._item_collection))
            return task._item_collection
        except Exception as err:
            task.logger.error(err, exc_info=True)
            raise err

    @classmethod
    def get_cli_parser(cls):
        """ Parse CLI arguments """
        dhf = argparse.ArgumentDefaultsHelpFormatter
        parser0 = argparse.ArgumentParser(description=cls.description)
        parser0.add_argument('--version', help='Print version and exit', action='version', version=cls.version)

        pparser = argparse.ArgumentParser(add_help=False)
        pparser.add_argument('--logging', default='INFO', help='DEBUG, INFO, WARN, ERROR, CRITICAL')

        subparsers = parser0.add_subparsers(dest='command')

        # run
        h = 'Process STAC Item Collection'
        parser = subparsers.add_parser('run', parents=[pparser], help=h, formatter_class=dhf)
        parser.add_argument('input', help='Full path of item collection to process (s3 or local)')
        h = 'Use this as work directory. Will be created but not deleted)'
        parser.add_argument('--workdir', help=h, default=None, type=Path)
        h = 'Skip uploading of any generated assets and resulting STAC Items'
        parser.add_argument('--skip-upload', dest='skip_upload', action='store_true', default=False)
        return parser0

    @classmethod
    def parse_args(cls, args, parser=None):
        if parser is None:
            parser = cls.get_cli_parser()
        # turn Namespace into dictionary
        pargs = vars(parser.parse_args(args))
        # only keep keys that are not None
        pargs = {k: v for k, v in pargs.items() if v is not None}

        if pargs.get('command', None) is None:
            parser.print_help()
            sys.exit(0)

        return pargs

    @classmethod
    def cli(cls, parser=None):
        args = cls.parse_args(sys.argv[1:], parser=parser)
        cmd = args.pop('command')

        # logging
        loglevel = args.pop('logging')
        logging.basicConfig(level=loglevel)
    
        # quiet these loud loggers
        quiet_loggers = ['botocore', 's3transfer', 'urllib3']
        for ql in quiet_loggers:
            logging.getLogger(ql).propagate = False

        if cmd == 'run':
            href = args.pop('input')
            if href.startswith('s3://'):
                item_collection = s3().read_json(href)
            else:
                # open local item collection
                with open(href) as f:
                    item_collection = json.loads(f.read())
            # run task handler
            output = cls.handler(item_collection, **args)
            return output