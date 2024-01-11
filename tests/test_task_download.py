import json
from pathlib import Path
from typing import Any, Dict

import pytest

from .tasks import NothingTask


@pytest.fixture
def item_collection() -> Dict[str, Any]:
    name = "sentinel2-l2a-j2k-payload"
    filename = Path(__file__).parent / "fixtures" / f"{name}.json"
    with open(filename) as f:
        items = json.loads(f.read())
    assert isinstance(items, dict)
    return items


def test_download_nosuch_asset(item_collection: Dict[str, Any]) -> None:
    t = NothingTask(
        item_collection,
    )
    item = t.download_item_assets(t.items[0], assets=["nosuch_asset"]).to_dict()
    # new item same as old item
    assert item["assets"] == t.items[0].to_dict()["assets"]


# @vcr.use_cassette(str(cassettepath / 'download_assets'))
def test_download_item_asset(tmp_path: Path, item_collection: Dict[str, Any]) -> None:
    t = NothingTask(item_collection, workdir=tmp_path / "test-task-download-item-asset")
    item = t.download_item_assets(t.items[0], assets=["tileinfo_metadata"]).to_dict()
    fname = item["assets"]["tileinfo_metadata"]["href"]
    filename = Path(fname)
    assert filename.is_file() is True


def test_download_keep_original_filenames(
    tmp_path: Path, item_collection: Dict[str, Any]
) -> None:
    t = NothingTask(
        item_collection,
        workdir=tmp_path / "test-task-download-item-asset",
    )
    item = t.download_item_assets(
        t.items[0], assets=["tileinfo_metadata"], keep_original_filenames=True
    ).to_dict()
    fname = item["assets"]["tileinfo_metadata"]["href"]
    filename = Path(fname)
    assert filename.name == "tileInfo.json"


def test_download_item_asset_local(
    tmp_path: Path, item_collection: Dict[str, Any]
) -> None:
    t = NothingTask(item_collection, workdir=tmp_path / "test-task-download-item-asset")
    item = t.download_item_assets(t.items[0], assets=["tileinfo_metadata"])
    fname = item.assets["tileinfo_metadata"].href
    filename = Path(fname)
    assert filename.is_file() is True
    # Downloaded to local, as in prev test.
    # With the asset hrefs updated by the prev download, we "download" again to subdir
    item = t.download_item_assets(
        item, assets=["tileinfo_metadata"], path_template="again/${collection}/${id}"
    )
    href = item.assets["tileinfo_metadata"].href
    assert "again" in href
    filename = Path(href)
    assert filename.is_file() is True


# @vcr.use_cassette(str(cassettepath / 'download_assets'))
def test_download_item_assets(tmp_path: Path, item_collection: Dict[str, Any]) -> None:
    t = NothingTask(
        item_collection,
        workdir=tmp_path / "test-task-download-item-assets",
        save_workdir=True,
    )
    item = t.download_item_assets(
        t.items[0], assets=["tileinfo_metadata", "granule_metadata"]
    ).to_dict()
    filename = Path(item["assets"]["tileinfo_metadata"]["href"])
    assert filename.is_file() is True
    filename = Path(item["assets"]["granule_metadata"]["href"])
    assert filename.is_file() is True


def test_download_items_assets(tmp_path: Path, item_collection: Dict[str, Any]) -> None:
    asset_key = "tileinfo_metadata"
    t = NothingTask(
        item_collection,
        workdir=tmp_path / "test-task-download-items-assets",
        save_workdir=True,
    )
    items = [i.to_dict() for i in t.download_items_assets(t.items, assets=[asset_key])]
    filename = Path(items[0]["assets"][asset_key]["href"])
    assert filename.is_file() is True
    filename = Path(items[1]["assets"][asset_key]["href"])
    assert filename.is_file() is True


# @vcr.use_cassette(str(cassettepath / 'download_assets'))
@pytest.mark.s3_requester_pays
def test_download_large_asset(tmp_path: Path, item_collection: Dict[str, Any]) -> None:
    t = NothingTask(
        item_collection,
        workdir=tmp_path / "test-task-download-assets",
        save_workdir=True,
    )
    item = t.download_item_assets(
        t.items[0], assets=["red"], requester_pays=True
    ).to_dict()
    filename = Path(item["assets"]["red"]["href"])
    assert filename.is_file() is True
    del t
