import json
import os
from pathlib import Path
from typing import Any

import pytest
import stac_asset

from stactask.config import DownloadConfig

from .tasks import NothingTask


@pytest.fixture
def item_collection() -> dict[str, Any]:
    name = "sentinel2-l2a-j2k-payload"
    filename = Path(__file__).parent / "fixtures" / f"{name}.json"
    with open(filename) as f:
        items = json.loads(f.read())
    assert isinstance(items, dict)
    return items


def test_download_nosuch_asset(tmp_path: Path, item_collection: dict[str, Any]) -> None:
    t = NothingTask(
        item_collection,
        workdir=tmp_path / "test-task-download-nosuch-asset",
        save_workdir=True,
    )
    item = t.download_item_assets(
        t.items[0], config=DownloadConfig(include=["nosuch_asset"])
    )

    # new item has same assets hrefs as old item
    assert [x.href for x in item.assets.values()] == [
        x.href for x in t.items[0].assets.values()
    ]


def test_download_asset_dont_keep_existing(
    tmp_path: Path, item_collection: dict[str, Any]
) -> None:
    t = NothingTask(
        item_collection,
        workdir=tmp_path / "test-task-download-nosuch-asset",
        save_workdir=True,
    )
    item = t.download_item_assets(
        t.items[0],
        config=DownloadConfig(include=["nosuch_asset"]),
        keep_non_downloaded=False,
    )

    # new item has no assets
    assert item.assets == {}


# @vcr.use_cassette(str(cassettepath / 'download_assets'))
def test_download_item_asset(tmp_path: Path, item_collection: dict[str, Any]) -> None:
    t = NothingTask(item_collection, workdir=tmp_path / "test-task-download-item-asset")
    item = t.download_item_assets(
        t.items[0], config=DownloadConfig(include=["tileinfo_metadata"])
    )
    assert Path(item.assets["tileinfo_metadata"].get_absolute_href()).is_file()


def test_download_keep_original_filenames(
    tmp_path: Path, item_collection: dict[str, Any]
) -> None:
    t = NothingTask(
        item_collection,
        workdir=tmp_path / "test-task-download-item-asset",
    )
    item = t.download_item_assets(
        t.items[0],
        config=DownloadConfig(
            include=["tileinfo_metadata"],
            file_name_strategy=stac_asset.FileNameStrategy.FILE_NAME,
        ),
    ).to_dict()
    fname = item["assets"]["tileinfo_metadata"]["href"]
    filename = Path(fname)
    assert filename.name == "tileInfo.json"


def test_download_item_asset_local(
    tmp_path: Path, item_collection: dict[str, Any]
) -> None:
    t = NothingTask(item_collection, workdir=tmp_path / "test-task-download-item-asset")
    item = t.download_item_assets(
        t.items[0], config=DownloadConfig(include=["tileinfo_metadata"])
    )

    assert (
        Path(os.path.dirname(item.self_href)) / item.assets["tileinfo_metadata"].href
    ).is_file()

    # Downloaded to local, as in prev test.
    # With the asset hrefs updated by the prev download, we "download" again to subdir
    item = t.download_item_assets(
        item=item,
        config=DownloadConfig(include=["tileinfo_metadata"]),
        path_template="again/${collection}/${id}",
    )
    assert "again" in item.self_href
    href = item.assets["tileinfo_metadata"].get_absolute_href()
    assert "again" in href
    assert Path(href).is_file()


# @vcr.use_cassette(str(cassettepath / 'download_assets'))
def test_download_item_assets(tmp_path: Path, item_collection: dict[str, Any]) -> None:
    t = NothingTask(
        item_collection,
        workdir=tmp_path / "test-task-download-item-assets",
        save_workdir=True,
    )
    item = t.download_item_assets(
        t.items[0],
        config=DownloadConfig(include=["tileinfo_metadata", "granule_metadata"]),
    )

    assert Path(item.assets["tileinfo_metadata"].get_absolute_href()).is_file()
    assert Path(item.assets["granule_metadata"].get_absolute_href()).is_file()


def test_download_items_assets(tmp_path: Path, item_collection: dict[str, Any]) -> None:
    asset_key = "tileinfo_metadata"
    t = NothingTask(
        item_collection,
        workdir=tmp_path / "test-task-download-items-assets",
        save_workdir=True,
    )
    items = t.download_items_assets(t.items, config=DownloadConfig(include=[asset_key]))

    assert len(items) == 2
    for item in items:
        assert Path(item.assets[asset_key].get_absolute_href()).is_file()


# @vcr.use_cassette(str(cassettepath / 'download_assets'))
@pytest.mark.s3_requester_pays
def test_download_large_asset(tmp_path: Path, item_collection: dict[str, Any]) -> None:
    t = NothingTask(
        item_collection,
        workdir=tmp_path / "test-task-download-assets",
        save_workdir=True,
    )
    item = t.download_item_assets(
        t.items[0], config=DownloadConfig(s3_requester_pays=True, include=["red"])
    )

    assert Path(item.assets["red"].get_absolute_href()).is_file()
