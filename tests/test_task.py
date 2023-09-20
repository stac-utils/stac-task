import datetime
from pathlib import Path
from typing import Callable

from pystac import Item
from stac_task import HrefTask, ItemTask, OneToOneTask
from stac_task.models import Href


def test_item_task() -> None:
    class AddPropertyTask(ItemTask):
        def process_item(self, item: Item) -> Item:
            item.properties["foo"] = "bar"
            return item

    item = Item(
        id="an-id",
        geometry=None,
        bbox=None,
        datetime=datetime.datetime.now(),
        properties={},
    )

    result = AddPropertyTask().process_dicts([item.to_dict()])
    assert result[0]["properties"]["foo"] == "bar"


def test_relative_href_task(data_path: Callable[[str], Path]) -> None:
    class RelativeHrefTask(HrefTask):
        def process_href(self, href: str) -> Item:
            return Item.from_file(href)

    task = RelativeHrefTask()
    task.payload_href = str(data_path("payload.json"))
    result = task.process([Href(href="./simple-item.json")])[0]
    assert result.id == "20201211_223832_CS2"


def test_working_directory(tmp_path: Path, data_path: Callable[[str], Path]) -> None:
    class DownloadTask(OneToOneTask[Href, Href]):
        def process_one_to_one(self, href: Href) -> Href:
            return Href(href=self.download_href(href.href))

    result = DownloadTask(working_directory=str(tmp_path)).process(
        [Href(href=str(data_path("simple-item.json")))]
    )
    assert result[0].href == str(tmp_path / "simple-item.json")
    Item.from_file(str(tmp_path / "simple-item.json"))
