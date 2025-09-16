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
            },
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
                        "upload_options": {"path_template": "/sentinel/${id}"},
                    },
                    "landsat-collection": {
                        "upload_options": {"path_template": "/landsat/${id}"},
                    },
                    "default-collection": {
                        "upload_options": {"path_template": "/default/${id}"},
                    },
                },
                "tasks": {
                    "new-task-a": {"new_param_a": "new_value_a"},
                    "new-task-b": {"new_param_b": "new_value_b"},
                },
            },
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
            },
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
                    },
                ],
                "tasks": {"test-task": {}},
            },
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
                    },
                ],
                "tasks": {"test-task": {}},
            },
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
                    },
                ],
                "tasks": {"test-task": {}},
            },
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


def test_upload_options_legacy(legacy_payload: dict[str, Any]) -> None:
    """Test upload_options property with legacy format."""
    payload = Payload(legacy_payload)
    expected = legacy_payload["process"][0]["upload_options"]
    assert payload.upload_options == expected


def test_upload_options_new(new_payload: dict[str, Any]) -> None:
    """Test upload_options property with new format."""
    payload = Payload(new_payload)
    expected = new_payload["process"][0]["upload_options"]
    assert payload.upload_options == expected


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


# 4. Expected Payload Property Errors Tests


def test_process_definition_error_not_list(new_payload: dict[str, Any]) -> None:
    """Test process_definition raises TypeError when process is not list or dict."""
    new_payload["process"] = "invalid_process"
    payload = Payload(new_payload)

    expected_msg = "unable to parse 'process': must be type list"
    with pytest.raises(TypeError, match=expected_msg):
        _ = payload.process_definition


def test_process_definition_error_first_not_dict(new_payload: dict[str, Any]) -> None:
    """Test process_definition raises TypeError when first element is not dict."""
    new_payload["process"] = ["not_a_dict"]
    payload = Payload(new_payload)

    expected_msg = (
        "unable to parse 'process': the first element of the list must be type dict"
    )
    with pytest.raises(TypeError, match=expected_msg):
        _ = payload.process_definition


def test_workflow_options_error_not_dict(new_payload: dict[str, Any]) -> None:
    """Test workflow_options raises TypeError when not dict."""
    new_payload["process"][0]["workflow_options"] = "not_a_dict"
    payload = Payload(new_payload)

    expected_msg = "unable to parse 'workflow_options': must be type dict"
    with pytest.raises(TypeError, match=expected_msg):
        _ = payload.workflow_options


def test_task_options_dict_error_not_dict_or_list(new_payload: dict[str, Any]) -> None:
    """Test task_options_dict raises TypeError when not dict or list."""
    new_payload["process"][0]["tasks"] = "not_dict_or_list"
    payload = Payload(new_payload)

    expected_msg = "unable to parse 'tasks': must be type dict or type list"
    with pytest.raises(TypeError, match=expected_msg):
        _ = payload.task_options_dict


def test_task_options_dict_error_params_not_dict(new_payload: dict[str, Any]) -> None:
    """Test task_options_dict raises TypeError when parameters not dict."""
    new_payload["process"][0]["tasks"] = [
        {"name": "test-task", "parameters": "not_a_dict"},
    ]
    payload = Payload(new_payload)

    expected_msg = (
        "unable to parse 'parameters' for task 'test-task': must be type dict"
    )
    with pytest.raises(TypeError, match=expected_msg):
        _ = payload.task_options_dict


def test_task_options_dict_error_options_not_dict(new_payload: dict[str, Any]) -> None:
    """Test task_options_dict raises TypeError when task options not dict."""
    new_payload["process"][0]["tasks"] = {"test-task": "not_a_dict"}
    payload = Payload(new_payload)

    expected_msg = "unable to parse options for task 'test-task': must be type dict"
    with pytest.raises(TypeError, match=expected_msg):
        _ = payload.task_options_dict


def test_items_as_dicts_error_features_not_list(new_payload: dict[str, Any]) -> None:
    """Test items_as_dicts raises ValueError when features not list."""
    new_payload["features"] = "not_a_list"
    payload = Payload(new_payload)

    with pytest.raises(
        TypeError,
        match="unable to parse 'features': must be type list",
    ):
        _ = payload.items_as_dicts


def test_upload_options_error_not_dict(new_payload: dict[str, Any]) -> None:
    """Test upload_options raises ValueError when upload_options not dict."""
    new_payload["process"][0]["upload_options"] = "not_a_dict"
    payload = Payload(new_payload)

    with pytest.raises(
        TypeError,
        match="unable to parse 'upload_options': must be type dict",
    ):
        _ = payload.upload_options


def test_collection_mapping_error_not_dict(legacy_payload: dict[str, Any]) -> None:
    """Test collection_mapping raises ValueError when collections not dict."""
    legacy_payload["process"][0]["upload_options"]["collections"] = "not_a_dict"
    payload = Payload(legacy_payload)

    with pytest.raises(
        TypeError,
        match="unable to parse 'collections': must be type dict",
    ):
        _ = payload.collection_mapping


def test_collection_matchers_error_not_list(new_payload: dict[str, Any]) -> None:
    """Test collection_matchers raises TypeError when not list."""
    new_payload["process"][0]["collection_matchers"] = "not_a_list"
    payload = Payload(new_payload)

    with pytest.raises(
        TypeError,
        match="unable to parse 'collection_matchers': must be type list",
    ):
        _ = payload.collection_matchers


def test_collection_matchers_error_not_dicts(new_payload: dict[str, Any]) -> None:
    """Test collection_matchers raises TypeError when matchers not dicts."""
    new_payload["process"][0]["collection_matchers"] = ["not_a_dict"]
    payload = Payload(new_payload)

    with pytest.raises(
        TypeError,
        match="unable to parse 'collection_matchers': each matcher must be type dict",
    ):
        _ = payload.collection_matchers


def test_collection_options_error_not_dict(new_payload: dict[str, Any]) -> None:
    """Test collection_options raises TypeError when not dict."""
    new_payload["process"][0]["collection_options"] = "not_a_dict"
    payload = Payload(new_payload)

    with pytest.raises(
        TypeError,
        match="unable to parse 'collection_options': must be type dict",
    ):
        _ = payload.collection_options


# 5. Expected Payload Method Errors Tests


def test_get_collection_options_error_not_dict(new_payload: dict[str, Any]) -> None:
    """Test get_collection_options raises TypeError when collection options not dict."""
    new_payload["process"][0]["collection_options"]["test-collection"] = "not_a_dict"
    payload = Payload(new_payload)

    expected_msg = (
        "unable to parse 'collection_options' for collection 'test-collection': "
        "must be type dict"
    )
    with pytest.raises(TypeError, match=expected_msg):
        payload.get_collection_options("test-collection")
