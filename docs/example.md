---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
---

# Example

We'll demonstrate one way to use **stac-task** by processing some [GOES mesoscale data](https://www.star.nesdis.noaa.gov/goes/meso_index.php).
This work is based on the [Element84/goes-meso-visualizer](https://github.com/Element84/goes-meso-visualizer) demo project.

## Workflow

For this work, we'll begin with a [STAC API search](https://api.stacspec.org/v1.0.0/item-search/#tag/Item-Search) against [Microsoft's Planetary Computer](https://planetarycomputer.microsoft.com/), which hosts [COG](https://www.cogeo.org/) versions of GOES data.
The results from that search are a feature collection of [STAC items](https://github.com/radiantearth/stac-spec/blob/master/item-spec/item-spec.md).
Some of the assets from the feature collection will be downloaded locally, and then processed through a series of steps until they are rendered to PNGs, projected into web mercator for visualization.
Here's a diagram:

![Workflow](img/workflow.png)

Each step in the workflow will be its own task.

## Defining tasks

Each task will call out to a function in **goes-meso-visualizer**, so all we need to do is write the wrappers and define the input and output structures.

```python
import datetime
from typing import Optional, Dict, Any, List

import goes_meso_visualizer.colorize
import goes_meso_visualizer.search
import goes_meso_visualizer.solarize
import goes_meso_visualizer.web_png
import pystac
import stac_task
from pydantic import BaseModel
from pystac import ItemCollection
from stac_task import OneToOneTask, OneToManyTask, StacInStacOutTask
from stac_task.models import Item, Asset


class SearchInput(BaseModel):
    intersects: Optional[Dict[str, Any]]
    start: datetime.datetime
    end: datetime.datetime
    max_items: Optional[int] = None
    exclude: Optional[List[str]] = None

class SolarizedAssets(BaseModel):
    C01_2km: Asset
    C02_2km: Asset
    C03_2km: Asset
    C13_2km: Asset
    solar_altitude: Asset

class ColorizedAssets(BaseModel):
    visual: Asset


class WebPngAssets(BaseModel):
    web_png: Asset


"""The items subclass `Item` and set the `assets` field to the appropriate data structure."""

class SolarizedItem(Item):
    assets: SolarizedAssets


class ColorizedItem(Item):
    assets: ColorizedAssets


class WebPngItem(Item):
    assets: WebPngAssets


"""These tasks actually define what happens."""

class SearchTask(OneToManyTask[SearchInput, Item]):
    input = SearchInput
    output = Item

    def process_one_to_many(self, input: SearchInput) -> List[Item]:
        item_collection = goes_meso_visualizer.search.goes(**input.model_dump())
        return [Item.from_pystac(item) for item in item_collection]


class DownloadTask(StacInStacOutTask):
    def process_items(self, input: List[pystac.Item]) -> List[pystac.Item]:
        item_collection = ItemCollection(input)
        # `download_item_collection` updates the hrefs to point to the local locations
        item_collection = self.download_item_collection(item_collection,
            include=["C01_2km", "C02_2km", "C03_2km", "C13_2km"])
        return list(item_collection)
 

class SolarizeTask(OneToOneTask[Item, SolarizedItem]):
    input = Item
    output = SolarizedItem

    def process_one_to_one(self, input: List[Item]) -> List[SolarizedItem]:
        solarized_item = goes_meso_visualizer.solarize.item(input.to_pystac())
        return SolarizedItem.from_pystac(solarized_item)


class ColorizeTask(OneToOneTask[SolarizedItem, ColorizedItem]):
    input = SolarizedItem
    output = ColorizedItem

    def process_one_to_one(self, input: SolarizedItem) -> ColorizedItem:
        colorized_item = goes_meso_visualizer.colorize.item(input.to_pystac())
        return ColorizedItem.from_pystac(colorized_item)


class WebPngTask(OneToOneTask[ColorizedItem, WebPngItem]):
    input = ColorizedItem
    output = WebPngItem

    def process_one_to_one(self, input: ColorizedItem) -> WebPngItem:
        web_png_item = goes_meso_visualizer.web_png.item(input.to_pystac())
        return WebPngItem.from_pystac(web_png_item)


"""Tasks must be registered with the library to be picked up by the process executor."""

stac_task.register_task("search", SearchTask)
stac_task.register_task("download", DownloadTask)
stac_task.register_task("solarize", SolarizeTask)
stac_task.register_task("colorize", ColorizeTask)
# `register_task` returns a context manager, so we capture the output so it
# doesn't show up in the notebook 
_ = stac_task.register_task("web-png", WebPngTask)
```

## Running a workflow

A workflow is defined by a payload and a list of task names.
One way to execute a workflow is to use the `Payload.execute_workflow` method.
We define our initial search criteria in the payload, as well as the working directory.
The payload could be a static JSON object, possibly saved in a file somewhere, or it could be constructed dynamically.
Here, we define it as a Python dictionary, then parse it into a `Payload` object before executing the workflow.

```python
from pathlib import Path

import nest_asyncio
from stac_task import Payload

# stac-asset, which handles downloading, uses asyncio.run in its blocking
# interface. This patch is necessary to use stac-task in a notebook environment,
# which has an asyncio runtime.
nest_asyncio.apply()

root = Path().cwd().parent

payload_dict = {
    "features": [{
        "intersects": {
            "type": "Point",
            "coordinates": [-109, 17],  # Hurricane Hilary
        },
        "start": datetime.datetime(2023, 8, 17),
        "end": datetime.datetime(2023, 8, 18),
        "max_items": 10,
    }],
    "process": {
        "tasks": {
            "search": {},
            "download": {},
            "solarize": {},
            "colorize": {},
            "web-png": {},
        },
        "config": {
            "working_directory": root / "tests" / "data" / "working-directory",
        }
    }
}
payload = Payload.model_validate(payload_dict)
result = payload.execute_workflow(["search", "download", "solarize", "colorize", "web-png"])
```

## Displaying the results

Because this example is a static website, it's tricky to display a dynamic map of the results; check out the [original repo](https://github.com/Element84/goes-meso-visualizer) for some demo pages.
To keep things simple, we simply visualize all of our PNGs:

```python
from IPython.display import Image, display

for item in result.features:
    href = item["assets"]["web_png"]["href"]
    display(Image(filename=href))
```
