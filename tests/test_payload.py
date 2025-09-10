from typing import Any

import pytest

from stactask.payload import Payload

# Test Fixtures


@pytest.fixture
def legacy_payload() -> dict[str, Any]:
    """Legacy payload using upload_options.collections."""
    return {
        "features": [
            {
                "id": "S2A_test",
                "type": "Feature",
                "properties": {"mission": "sentinel"},
            },
            {"id": "L8_test", "type": "Feature", "properties": {"mission": "landsat"}},
        ],
        "process": [
            {
                "workflow": "test-workflow",
                "workflow_options": {"global_param": "global_value"},
                "upload_options": {
                    "path_template": "/legacy/${collection}/${id}",
                    "collections": {
                        "sentinel-2": "$[?(@.id =~ 'S2[AB].*')]",
                        "landsat-8": "$[?(@.id =~ 'L8.*')]",
                    },
                },
                "tasks": {
                    "task-a": {"param_a": "value_a"},
                    "task-b": {"param_b": "value_b"},
                },
            }
        ],
    }


@pytest.fixture
def new_payload() -> dict[str, Any]:
    """New payload using collection_matchers and collection_options."""
    return {
        "features": [
            {
                "id": "sentinel-item",
                "type": "Feature",
                "properties": {"mission": "sentinel"},
            },
            {
                "id": "landsat-item",
                "type": "Feature",
                "properties": {"mission": "landsat"},
            },
            {
                "id": "unknown-item",
                "type": "Feature",
                "properties": {"mission": "modis"},
            },
        ],
        "process": [
            {
                "workflow": "new-workflow",
                "workflow_options": {"new_global_param": "new_global_value"},
                "upload_options": {"path_template": "/global/${collection}/${id}"},
                "collection_matchers": [
                    {
                        "type": "jsonpath",
                        "pattern": "$[?(@.properties.mission == 'sentinel')]",
                        "collection_name": "sentinel-collection",
                    },
                    {
                        "type": "jsonpath",
                        "pattern": "$[?(@.properties.mission == 'landsat')]",
                        "collection_name": "landsat-collection",
                    },
                    {"type": "catch_all", "collection_name": "default-collection"},
                ],
                "collection_options": {
                    "sentinel-collection": {
                        "upload_options": {"path_template": "/sentinel/${id}"}
                    },
                    "landsat-collection": {
                        "upload_options": {"path_template": "/landsat/${id}"}
                    },
                    "default-collection": {
                        "upload_options": {"path_template": "/default/${id}"}
                    },
                },
                "tasks": {
                    "new-task-a": {"new_param_a": "new_value_a"},
                    "new-task-b": {"new_param_b": "new_value_b"},
                },
            }
        ],
    }


@pytest.fixture
def payload_missing_both_collection_configs() -> dict[str, Any]:
    """Payload missing both collection_matchers and legacy collections."""
    return {
        "features": [{"id": "test-item", "type": "Feature"}],
        "process": [
            {
                "workflow": "test-workflow",
                "upload_options": {"path_template": "/test/${id}"},
                "tasks": {"test-task": {}},
            }
        ],
    }


@pytest.fixture
def payload_with_both_collection_configs() -> dict[str, Any]:
    """Payload with both collection_matchers and legacy collections."""
    return {
        "features": [{"id": "test-item", "type": "Feature"}],
        "process": [
            {
                "workflow": "test-workflow",
                "upload_options": {
                    "path_template": "/test/${id}",
                    "collections": {"test-collection": "$[?(@.id == 'test-item')]"},
                },
                "collection_matchers": [
                    {
                        "type": "jsonpath",
                        "pattern": "$[?(@.id == 'test-item')]",
                        "collection_name": "test-collection",
                    }
                ],
                "tasks": {"test-task": {}},
            }
        ],
    }


@pytest.fixture
def payload_collection_missing_upload_options() -> dict[str, Any]:
    """Payload with collection matcher and global upload options but missing upload
    options for collection."""
    return {
        "features": [{"id": "test-item", "type": "Feature"}],
        "process": [
            {
                "workflow": "test-workflow",
                "upload_options": {"path_template": "/global/${id}"},
                "collection_matchers": [
                    {
                        "type": "jsonpath",
                        "pattern": "$[?(@.id == 'test-item')]",
                        "collection_name": "missing-options-collection",
                    }
                ],
                "tasks": {"test-task": {}},
            }
        ],
    }


@pytest.fixture
def payload_collection_missing_upload_options_and_global_upload_options() -> (
    dict[str, Any]
):
    """Payload with collection matcher but missing global upload options and upload
    options for collection."""
    return {
        "features": [{"id": "test-item", "type": "Feature"}],
        "process": [
            {
                "workflow": "test-workflow",
                "collection_matchers": [
                    {
                        "type": "jsonpath",
                        "pattern": "$[?(@.id == 'test-item')]",
                        "collection_name": "missing-options-collection",
                    }
                ],
                "tasks": {"test-task": {}},
            }
        ],
    }


# 1. Payload Class Instantiation and Validation Tests


def test_payload_instantiation_and_validation_legacy(
    legacy_payload: dict[str, Any],
) -> None:
    """Test validation method with legacy format."""
    payload = Payload(legacy_payload)
    # Should not raise any exception
    payload.validate()


def test_payload_instantiation_and_validation_new(
    new_payload: dict[str, Any],
) -> None:
    """Test validation method with new format."""
    payload = Payload(new_payload)
    # Should not raise any exception
    payload.validate()


def test_validation_missing_both_collection_configs(
    payload_missing_both_collection_configs: dict[str, Any],
) -> None:
    """Test validation fails when both collection_matchers and legacy
    upload_options.collections are missing."""
    payload = Payload(payload_missing_both_collection_configs)

    expected_msg = (
        "'collection_matchers' or the legacy 'upload_options.collections' "
        "must be provided"
    )
    with pytest.raises(ValueError, match=expected_msg):
        payload.validate()


def test_validation_both_collection_configs_present(
    payload_with_both_collection_configs: dict[str, Any],
) -> None:
    """Test validation fails when both collection collection_matchers and legacy
    upload_options.collections are present."""
    payload = Payload(payload_with_both_collection_configs)

    expected_msg = (
        "A payload must not contain both 'collection_matchers' and the legacy "
        "'upload_options.collections'"
    )
    with pytest.raises(ValueError, match=expected_msg):
        payload.validate()


def test_validation_collection_missing_upload_options(
    payload_collection_missing_upload_options: dict[str, Any],
) -> None:
    """Test validation calls get_collection_upload_options for each collection."""
    payload = Payload(payload_collection_missing_upload_options)

    # This should not raise an error because get_collection_upload_options
    # will fall back to global upload options if collection-specific options are missing
    payload.validate()


def test_validation_collection_missing_upload_options_and_global_upload_options(
    payload_collection_missing_upload_options_and_global_upload_options: dict[str, Any],
) -> None:
    """Test validation fails when no global upload options are available."""
    payload = Payload(
        payload_collection_missing_upload_options_and_global_upload_options
    )

    # This should raise an error because get_collection_upload_options
    # cannot fall back to global upload options when they don't exist
    expected_msg = "No upload options found for collection 'missing-options-collection'"
    with pytest.raises(ValueError, match=expected_msg):
        payload.validate()


# 2. Payload Properties Tests


def test_process_definition_legacy(legacy_payload: dict[str, Any]) -> None:
    """Test process_definition property with legacy format."""
    payload = Payload(legacy_payload)
    process_def = payload.process_definition
    assert process_def == legacy_payload["process"][0]


def test_process_definition_new(new_payload: dict[str, Any]) -> None:
    """Test process_definition property with new format."""
    payload = Payload(new_payload)
    process_def = payload.process_definition
    assert process_def == new_payload["process"][0]


def test_workflow_options_legacy(legacy_payload: dict[str, Any]) -> None:
    """Test workflow_options property with legacy format."""
    payload = Payload(legacy_payload)
    expected = legacy_payload["process"][0]["workflow_options"]
    assert payload.workflow_options == expected


def test_workflow_options_new(new_payload: dict[str, Any]) -> None:
    """Test workflow_options property with new format."""
    payload = Payload(new_payload)
    expected = new_payload["process"][0]["workflow_options"]
    assert payload.workflow_options == expected


def test_task_options_dict_legacy(legacy_payload: dict[str, Any]) -> None:
    """Test task_options_dict property with legacy format."""
    payload = Payload(legacy_payload)
    expected = legacy_payload["process"][0]["tasks"]
    assert payload.task_options_dict == expected


def test_task_options_dict_new(new_payload: dict[str, Any]) -> None:
    """Test task_options_dict property with new format."""
    payload = Payload(new_payload)
    expected = new_payload["process"][0]["tasks"]
    assert payload.task_options_dict == expected


def test_items_as_dicts_legacy(legacy_payload: dict[str, Any]) -> None:
    """Test items_as_dicts property with legacy format."""
    payload = Payload(legacy_payload)
    expected = legacy_payload["features"]
    assert payload.items_as_dicts == expected


def test_items_as_dicts_new(new_payload: dict[str, Any]) -> None:
    """Test items_as_dicts property with new format."""
    payload = Payload(new_payload)
    expected = new_payload["features"]
    assert payload.items_as_dicts == expected


def test_global_upload_options_legacy(legacy_payload: dict[str, Any]) -> None:
    """Test global_upload_options property with legacy format."""
    payload = Payload(legacy_payload)
    expected = legacy_payload["process"][0]["upload_options"]
    assert payload.global_upload_options == expected


def test_global_upload_options_new(new_payload: dict[str, Any]) -> None:
    """Test global_upload_options property with new format."""
    payload = Payload(new_payload)
    expected = new_payload["process"][0]["upload_options"]
    assert payload.global_upload_options == expected


def test_collection_mapping_legacy(legacy_payload: dict[str, Any]) -> None:
    """Test collection_mapping property with legacy format."""
    payload = Payload(legacy_payload)
    expected = legacy_payload["process"][0]["upload_options"]["collections"]
    assert payload.collection_mapping == expected


def test_collection_mapping_new(new_payload: dict[str, Any]) -> None:
    """Test collection_mapping property with new format (should be empty)."""
    payload = Payload(new_payload)
    assert payload.collection_mapping == {}


def test_collection_matchers_legacy(legacy_payload: dict[str, Any]) -> None:
    """Test collection_matchers property with legacy format (should be empty)."""
    payload = Payload(legacy_payload)
    assert payload.collection_matchers == []


def test_collection_matchers_new(new_payload: dict[str, Any]) -> None:
    """Test collection_matchers property with new format."""
    payload = Payload(new_payload)
    expected = new_payload["process"][0]["collection_matchers"]
    assert payload.collection_matchers == expected


def test_collection_options_legacy(legacy_payload: dict[str, Any]) -> None:
    """Test collection_options property with legacy format (should be empty)."""
    payload = Payload(legacy_payload)
    assert payload.collection_options == {}


def test_collection_options_new(new_payload: dict[str, Any]) -> None:
    """Test collection_options property with new format."""
    payload = Payload(new_payload)
    expected = new_payload["process"][0]["collection_options"]
    assert payload.collection_options == expected


# 3. Payload Methods Tests


def test_get_collection_options_legacy(legacy_payload: dict[str, Any]) -> None:
    """Test get_collection_options method with legacy format."""
    payload = Payload(legacy_payload)

    # Should return empty dict for any collection name in legacy format
    assert payload.get_collection_options("sentinel-2") == {}
    assert payload.get_collection_options("nonexistent") == {}


def test_get_collection_options_new(new_payload: dict[str, Any]) -> None:
    """Test get_collection_options method with new format."""
    payload = Payload(new_payload)

    # Test existing collection
    collection_options = new_payload["process"][0]["collection_options"]
    expected = collection_options["sentinel-collection"]
    assert payload.get_collection_options("sentinel-collection") == expected

    # Test nonexistent collection
    assert payload.get_collection_options("nonexistent") == {}


def test_get_collection_upload_options_legacy(
    legacy_payload: dict[str, Any],
) -> None:
    """Test get_collection_upload_options method with legacy format."""
    payload = Payload(legacy_payload)

    # Should return global upload options for any collection
    expected = legacy_payload["process"][0]["upload_options"]
    assert payload.get_collection_upload_options("sentinel-2") == expected
    assert payload.get_collection_upload_options("nonexistent") == expected


def test_get_collection_upload_options_new(new_payload: dict[str, Any]) -> None:
    """Test get_collection_upload_options method with new format."""
    payload = Payload(new_payload)

    # Test collection with specific upload options
    collection_options = new_payload["process"][0]["collection_options"]
    expected_sentinel = collection_options["sentinel-collection"]["upload_options"]
    result = payload.get_collection_upload_options("sentinel-collection")
    assert result == expected_sentinel

    # Test collection falling back to global options
    expected_global = new_payload["process"][0]["upload_options"]
    assert payload.get_collection_upload_options("nonexistent") == expected_global
