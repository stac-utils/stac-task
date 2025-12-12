from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pystac import Item

from stactask.task import Task


class TestTask(Task):
    """Test task implementation."""

    name = "test-task"

    def process(self, **kwargs: Any) -> list[dict[str, Any]]:
        return []


def create_test_item() -> Item:
    """Create a test STAC Item."""
    return Item(
        id="test-item-123",
        geometry={"type": "Point", "coordinates": [0, 0]},
        bbox=[0, 0, 0, 0],
        datetime=datetime.now(timezone.utc),
        properties={},
        collection="test-collection",
    )


def test_upload_item_to_s3_success() -> None:
    """Test successful item upload with all updates."""
    # Arrange
    payload = {
        "type": "FeatureCollection",
        "features": [],
        "process": {
            "upload_options": {
                "path_template": "s3://test-bucket/${collection}/${year}/${month}/${day}",
            },
        },
    }
    task = TestTask(payload, upload=True)
    item = create_test_item()
    mock_s3_client = MagicMock()
    mock_s3_client.exists.return_value = False

    # Act
    with patch("stactask.asset_io.global_s3_client", mock_s3_client):
        task.upload_item_to_s3(item, s3_client=mock_s3_client)

    # Assert
    assert "created" in item.properties
    assert "updated" in item.properties
    assert item.properties["created"] == item.properties["updated"]

    canonical_links = [link for link in item.links if link.rel == "canonical"]
    self_links = [link for link in item.links if link.rel == "self"]
    assert len(canonical_links) == 1
    assert len(self_links) == 1
    assert "s3://test-bucket/" in str(canonical_links[0].target)
    assert item.id in str(canonical_links[0].target)

    mock_s3_client.upload_json.assert_called_once()
    call_args = mock_s3_client.upload_json.call_args
    assert call_args[0][0]["id"] == "test-item-123"
    assert "s3://test-bucket/" in call_args[0][1]


def test_upload_item_to_s3_existing_item_preserves_created() -> None:
    """Test that existing item's created timestamp is preserved."""
    # Arrange
    original_created = "2024-01-01T00:00:00Z"
    payload = {
        "type": "FeatureCollection",
        "features": [],
        "process": {
            "upload_options": {
                "path_template": "s3://test-bucket/${collection}",
            },
        },
    }
    task = TestTask(payload, upload=True)
    item = create_test_item()

    mock_s3_client = MagicMock()
    mock_s3_client.exists.return_value = True
    mock_s3_client.read_json.return_value = {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": "existing-item",
        "geometry": {"type": "Point", "coordinates": [0, 0]},
        "bbox": [0, 0, 0, 0],
        "properties": {
            "datetime": "2024-01-01T00:00:00Z",
            "created": original_created,
        },
        "links": [],
        "assets": {},
    }

    # Act
    with patch("stactask.asset_io.global_s3_client", mock_s3_client):
        task.upload_item_to_s3(item, s3_client=mock_s3_client)

    # Assert
    assert item.properties["created"] == original_created
    assert item.properties["updated"] != original_created
    mock_s3_client.exists.assert_called_once()
    mock_s3_client.read_json.assert_called_once()
    mock_s3_client.upload_json.assert_called_once()


def test_upload_item_to_s3_no_upload_flag() -> None:
    """Test that upload is skipped when upload flag is False."""
    # Arrange
    payload = {
        "type": "FeatureCollection",
        "features": [],
        "process": {
            "upload_options": {
                "path_template": "s3://test-bucket/${collection}",
            },
        },
    }
    task = TestTask(payload, upload=False)
    item = create_test_item()
    mock_s3_client = MagicMock()

    # Act
    task.upload_item_to_s3(item, s3_client=mock_s3_client)

    # Assert
    mock_s3_client.upload_json.assert_not_called()


def test_upload_item_to_s3_missing_path_template() -> None:
    """Test that ValueError is raised when path_template is missing."""
    # Arrange
    payload = {
        "type": "FeatureCollection",
        "features": [],
        "process": {
            "upload_options": {},
        },
    }
    task = TestTask(payload, upload=True)
    item = create_test_item()

    # Act & Assert
    with pytest.raises(ValueError, match="Missing required 'path_template'"):
        task.upload_item_to_s3(item)


def test_upload_item_to_s3_removes_existing_links() -> None:
    """Test that existing self/canonical links are removed."""
    # Arrange
    payload = {
        "type": "FeatureCollection",
        "features": [],
        "process": {
            "upload_options": {
                "path_template": "s3://test-bucket/${collection}",
            },
        },
    }
    task = TestTask(payload, upload=True)
    item = create_test_item()

    # Add existing self and canonical links
    from pystac import Link

    item.add_link(Link(rel="self", target="http://old-url.com/item.json"))
    item.add_link(Link(rel="canonical", target="http://old-canonical.com/item.json"))
    item.add_link(Link(rel="root", target="http://root.com/catalog.json"))

    mock_s3_client = MagicMock()
    mock_s3_client.exists.return_value = False

    # Act
    with patch("stactask.asset_io.global_s3_client", mock_s3_client):
        task.upload_item_to_s3(item, s3_client=mock_s3_client)

    # Assert
    self_links = [link for link in item.links if link.rel == "self"]
    canonical_links = [link for link in item.links if link.rel == "canonical"]
    root_links = [link for link in item.links if link.rel == "root"]

    assert len(self_links) == 1
    assert len(canonical_links) == 1
    assert len(root_links) == 1

    assert "s3://test-bucket/" in str(self_links[0].target)
    assert "old-url.com" not in str(self_links[0].target)

    assert "s3://test-bucket/" in str(canonical_links[0].target)
    assert "old-canonical.com" not in str(canonical_links[0].target)

    assert root_links[0].target == "http://root.com/catalog.json"
