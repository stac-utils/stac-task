import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict
from pystac import Item
from stac_task import (
    Anything,
    HrefTask,
    ItemTask,
    Nothing,
    OneToManyTask,
    OneToOneTask,
    StacInStacOutTask,
    StacOutTask,
    Task,
    ToItemTask,
)
from stac_task.models import Href


class PassthroughTask(OneToOneTask[Anything, Anything]):
    def process_one_to_one(self, input: Anything) -> Anything:
        return input


class TheMeaningOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    the_meaning: int


class TheMeaningTask(OneToOneTask[Nothing, TheMeaningOutput]):
    input = Nothing
    output = TheMeaningOutput

    foo: Optional[bool] = None

    def process_one_to_one(self, input: Nothing) -> TheMeaningOutput:
        fields: Dict[str, Any] = {"the_meaning": 42}
        if self.foo:
            fields["foo"] = "bar"
        return TheMeaningOutput(**fields)


class TestTask(Task[Anything, Anything]):
    __test__ = False

    def process(self, input: List[Anything]) -> List[Anything]:
        input.append(Anything.model_validate({"extra": "item"}))
        return input


class TestOneToManyTask(OneToManyTask[Anything, Anything]):
    __test__ = False

    def process_one_to_many(self, input: Anything) -> List[Anything]:
        return [input, input]


class TestStacInStacOutTask(StacInStacOutTask):
    __test__ = False

    href: str

    def process_items(self, input: List[Item]) -> List[Item]:
        input.append(Item.from_file(self.href))
        return input


class TestStacOutTask(StacOutTask[Href]):
    __test__ = False

    def process_to_items(self, input: List[Href]) -> List[Item]:
        return [Item.from_file(href.href) for href in input]


class TestToItemTask(ToItemTask[Href]):
    __test__ = False

    def process_to_item(self, input: Href) -> Item:
        return Item.from_file(input.href)


class TestItemTask(ItemTask):
    __test__ = False

    def process_item(self, item: Item) -> Item:
        item.properties["foo"] = "bar"
        return item


class TestHrefTask(HrefTask):
    __test__ = False

    def process_href(self, href: str) -> Item:
        return Item.from_file(href)


class DownloadTask(OneToOneTask[Href, Href]):
    def process_one_to_one(self, href: Href) -> Href:
        return Href(href=self.download_href(href.href))


class CopyTask(ItemTask):
    destination: Path

    def process_item(self, item: Item) -> Item:
        item = self.download_item(item)
        self.upload_item(item, str(self.destination))


def test_item_task() -> None:
    item = Item(
        id="an-id",
        geometry=None,
        bbox=None,
        datetime=datetime.datetime.now(),
        properties={},
    )

    result = TestItemTask().process_dicts([item.to_dict()])
    assert result[0]["properties"]["foo"] == "bar"


def test_relative_href_task(data_path: Path) -> None:
    task = TestHrefTask()
    task.payload_href = str(data_path / "payload.json")
    result = task.process([Href(href="./simple-item.json")])[0]
    assert result.id == "20201211_223832_CS2"


def test_working_directory(tmp_path: Path, data_path: Path) -> None:
    result = DownloadTask(working_directory=tmp_path).process(
        [Href(href=str(data_path / "simple-item.json"))]
    )
    assert result[0].href == str(tmp_path / "simple-item.json")
    Item.from_file(str(tmp_path / "simple-item.json"))


def test_task() -> None:
    assert TestTask().process_dicts([{"foo": "bar"}]) == [
        {"foo": "bar"},
        {"extra": "item"},
    ]


def test_one_to_many_task() -> None:
    assert TestOneToManyTask().process_dicts([{"foo": "bar"}]) == [
        {"foo": "bar"},
        {"foo": "bar"},
    ]


def test_stac_in_stac_out_task(data_path: Path) -> None:
    item = Item(
        id="an-id",
        geometry=None,
        bbox=None,
        datetime=datetime.datetime.now(),
        properties={},
    )
    assert (
        len(
            TestStacInStacOutTask(
                href=str(data_path / "simple-item.json")
            ).process_dicts([item.to_dict(transform_hrefs=False)])
        )
        == 2
    )


def test_stac_out_task(data_path: Path) -> None:
    assert (
        len(
            TestStacOutTask().process_dicts(
                [{"href": str(data_path / "simple-item.json")}]
            )
        )
        == 1
    )


def test_to_item_test(data_path: Path) -> None:
    assert (
        len(
            TestToItemTask().process_dicts(
                [{"href": str(data_path / "simple-item.json")}]
            )
        )
        == 1
    )


def test_copy_item(data_path: Path, tmp_path: Path, item: Item) -> None:
    CopyTask(
        working_directory=data_path / "working-directory", destination=tmp_path
    ).process_item(item)
