import json
from pathlib import Path

import pytest

from .tasks import NothingTask


testpath = Path(__file__).parent

def get_test_items(name="sentinel2-l2a-j2k-items"):
    filename = testpath / "fixtures" / f"{name}.json"
    with open(filename) as f:
        items = json.loads(f.read())
    return items



def test_download_nosuch_asset():
    t = NothingTask(
        get_test_items(),
    )
    item = t.download_item_assets(t.items[0], assets=["nosuch_asset"]).to_dict()
    # new item same as old item
    assert item['assets'] == t.items[0].to_dict()['assets']

# @vcr.use_cassette(str(cassettepath / 'download_assets'))
def test_download_asset():
    t = NothingTask(
        get_test_items(),
        workdir=testpath / "test-task-download-asset"
    )
    item = t.download_item_assets(t.items[0], assets=["tileinfo_metadata"]).to_dict()
    fname = item["assets"]["tileinfo_metadata"]["href"]
    filename = Path(fname)
    assert filename.is_file() is True
    del t
    assert filename.is_file() is False

# @vcr.use_cassette(str(cassettepath / 'download_assets'))
def test_download_assets():
    t = NothingTask(
        get_test_items(),
        workdir=testpath / "test-task-download-assets",
        save_workdir=True,
    )
    item = t.download_item_assets(t.items[0], assets=["tileinfo_metadata", "granule_metadata"]).to_dict()
    filename = Path(item["assets"]["tileinfo_metadata"]["href"])
    assert filename.is_file() is True
    filename = Path(item["assets"]["granule_metadata"]["href"])
    assert filename.is_file() is True


# @vcr.use_cassette(str(cassettepath / 'download_assets'))
@pytest.mark.slow
def test_download_large_asset():
    t = NothingTask(
        get_test_items(),
        workdir=testpath / "test-task-download-assets",
        save_workdir=True,
    )
    item = t.download_item_assets(
        t.items[0], assets=["red"], requester_pays=True
    ).to_dict()
    filename = Path(item["assets"]["red"]["href"])
    assert filename.is_file() is True
    # t._save_workdir = False
    del t
    # assert (filename.is_file() is False)