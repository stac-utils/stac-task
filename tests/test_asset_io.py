"""Tests for asset_io functions."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from pystac import Item

from stactask.asset_io import read_s3_item_json, upload_item_json_to_s3
from stactask.exceptions import PystacConversionError, StorageReadError


def create_test_item() -> Item:
    """Create a test STAC Item."""
    return Item(
        id="test-item",
        geometry={"type": "Point", "coordinates": [0, 0]},
        bbox=[0, 0, 0, 0],
        datetime=datetime.now(timezone.utc),
        properties={},
    )


def test_upload_item_json_to_s3_with_client() -> None:
    """Test upload with provided s3_client."""
    # Arrange
    item = create_test_item()
    url = "s3://test-bucket/test-collection/test-item.json"
    mock_s3_client = MagicMock()

    # Act
    upload_item_json_to_s3(item, url, s3_client=mock_s3_client, public=False)

    # Assert
    mock_s3_client.upload_json.assert_called_once()
    call_args = mock_s3_client.upload_json.call_args
    assert call_args[0][0]["id"] == "test-item"
    assert call_args[0][0]["type"] == "Feature"
    assert call_args[0][1] == url
    assert call_args[1]["public"] is False


def test_upload_item_json_to_s3_default_client() -> None:
    """Test upload with default global_s3_client."""
    # Arrange
    item = create_test_item()
    url = "s3://test-bucket/test-collection/test-item.json"
    mock_global_client = MagicMock()

    # Act
    with patch("stactask.asset_io.global_s3_client", mock_global_client):
        upload_item_json_to_s3(item, url, public=True)

    # Assert
    mock_global_client.upload_json.assert_called_once()
    call_args = mock_global_client.upload_json.call_args
    assert call_args[0][0]["id"] == "test-item"
    assert call_args[0][0]["type"] == "Feature"
    assert call_args[0][1] == url
    assert call_args[1]["public"] is True


def test_upload_item_json_to_s3_public_flag() -> None:
    """Test that public flag is passed correctly."""
    # Arrange
    item = create_test_item()
    url = "s3://test-bucket/item.json"
    mock_s3_client = MagicMock()

    # Act - public=True
    upload_item_json_to_s3(item, url, s3_client=mock_s3_client, public=True)

    # Assert
    call_kwargs = mock_s3_client.upload_json.call_args[1]
    assert call_kwargs["public"] is True

    # Act - public=False
    upload_item_json_to_s3(item, url, s3_client=mock_s3_client, public=False)

    # Assert
    call_kwargs = mock_s3_client.upload_json.call_args[1]
    assert call_kwargs["public"] is False


def test_read_s3_item_json_exists_and_valid() -> None:
    """Test reading a valid STAC Item from S3."""
    # Arrange
    url = "s3://test-bucket/test-collection/test-item.json"
    mock_s3_client = MagicMock()
    mock_s3_client.exists.return_value = True
    mock_s3_client.read_json.return_value = {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": "test-item",
        "geometry": {"type": "Point", "coordinates": [0, 0]},
        "bbox": [0, 0, 0, 0],
        "properties": {
            "datetime": "2024-01-01T00:00:00Z",
            "created": "2024-01-01T00:00:00Z",
        },
        "links": [],
        "assets": {},
    }

    # Act
    item = read_s3_item_json(url, s3_client=mock_s3_client)

    # Assert
    assert item is not None
    assert isinstance(item, Item)
    assert item.id == "test-item"
    assert item.properties["created"] == "2024-01-01T00:00:00Z"
    mock_s3_client.exists.assert_called_once_with(url)
    mock_s3_client.read_json.assert_called_once_with(url)


def test_read_s3_item_json_does_not_exist() -> None:
    """Test reading from S3 when item doesn't exist."""
    # Arrange
    url = "s3://test-bucket/nonexistent-item.json"
    mock_s3_client = MagicMock()
    mock_s3_client.exists.return_value = False

    # Act
    item = read_s3_item_json(url, s3_client=mock_s3_client)

    # Assert
    assert item is None
    mock_s3_client.exists.assert_called_once_with(url)
    mock_s3_client.read_json.assert_not_called()


def test_read_s3_item_json_cannot_parse() -> None:
    """Test reading from S3 when JSON can't be parsed as STAC Item."""
    # Arrange
    url = "s3://test-bucket/invalid-item.json"
    mock_s3_client = MagicMock()
    mock_s3_client.exists.return_value = True
    mock_s3_client.read_json.return_value = {"invalid": "data"}

    # Act / Assert: conversion should raise PystacConversionError
    with pytest.raises(PystacConversionError):
        read_s3_item_json(url, s3_client=mock_s3_client)

    mock_s3_client.exists.assert_called_once_with(url)
    mock_s3_client.read_json.assert_called_once_with(url)


def test_read_s3_item_json_read_fails() -> None:
    """Test reading from S3 when read_json raises an exception."""
    # Arrange
    url = "s3://test-bucket/item.json"
    mock_s3_client = MagicMock()
    mock_s3_client.exists.return_value = True
    mock_s3_client.read_json.side_effect = Exception("Network error")

    # Act / Assert: retrieval should raise StorageReadError
    with pytest.raises(StorageReadError):
        read_s3_item_json(url, s3_client=mock_s3_client)

    mock_s3_client.exists.assert_called_once_with(url)
    mock_s3_client.read_json.assert_called_once_with(url)


def test_read_s3_item_json_uses_global_client() -> None:
    """Test that read_s3_item_json uses global_s3_client when none provided."""
    # Arrange
    url = "s3://test-bucket/test-item.json"
    mock_global_client = MagicMock()
    mock_global_client.exists.return_value = True
    mock_global_client.read_json.return_value = {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": "global-test-item",
        "geometry": {"type": "Point", "coordinates": [0, 0]},
        "bbox": [0, 0, 0, 0],
        "properties": {"datetime": "2024-01-01T00:00:00Z"},
        "links": [],
        "assets": {},
    }

    # Act
    with patch("stactask.asset_io.global_s3_client", mock_global_client):
        item = read_s3_item_json(url)

    # Assert
    assert item is not None
    assert item.id == "global-test-item"
    mock_global_client.exists.assert_called_once_with(url)
    mock_global_client.read_json.assert_called_once_with(url)


def test_read_s3_item_json_with_custom_client() -> None:
    """Test that read_s3_item_json uses custom s3_client when provided."""
    # Arrange
    url = "s3://test-bucket/test-item.json"
    custom_client = MagicMock()
    custom_client.exists.return_value = True
    custom_client.read_json.return_value = {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": "custom-test-item",
        "geometry": {"type": "Point", "coordinates": [0, 0]},
        "bbox": [0, 0, 0, 0],
        "properties": {"datetime": "2024-01-01T00:00:00Z"},
        "links": [],
        "assets": {},
    }

    # Act
    item = read_s3_item_json(url, s3_client=custom_client)

    # Assert
    assert item is not None
    assert item.id == "custom-test-item"
    custom_client.exists.assert_called_once_with(url)
    custom_client.read_json.assert_called_once_with(url)
