import datetime

import pystac
from stac_task.models import Item, Properties


def test_item_to_pystac() -> None:
    item = Item(
        id="an-id", properties=Properties(datetime=datetime.datetime.now().isoformat())
    ).to_pystac()
    assert item.id == "an-id"
    assert isinstance(item.datetime, datetime.datetime)


def test_item_from_pystac() -> None:
    item = Item.from_pystac(
        pystac.Item(
            "an-id",
            geometry=None,
            bbox=None,
            datetime=datetime.datetime.now(),
            properties={},
        )
    )
    assert item.id == "an-id"
