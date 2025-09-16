from stactask.utils import find_collection, stac_jsonpath_match


def test_stac_jsonpath_match() -> None:
    assert stac_jsonpath_match({"id": "1"}, "$[?(@.id =~ '.*')]")
    assert stac_jsonpath_match({"id": "1"}, "$[?(@.id == '1')]")
    assert not stac_jsonpath_match(
        {"properties": {"s2:processing_baseline": "04.00"}},
        "$[?(@.properties.['s2:processing_baseline'] >= '05.00')]",
    )
    assert stac_jsonpath_match(
        {"properties": {"s2:processing_baseline": "05.00"}},
        "$[?(@.properties.['s2:processing_baseline'] >= '05.00')]",
    )
    assert stac_jsonpath_match(
        {"properties": {"s2:processing_baseline": "04.00"}},
        "$[?(@.properties.['s2:processing_baseline'] =~ '^04')]",
    )
    assert not stac_jsonpath_match(
        {"properties": {"s2:processing_baseline": "05.00"}},
        "$[?(@.properties.['s2:processing_baseline'] =~ '^04')]",
    )


def test_find_collection_with_mapping() -> None:
    assert find_collection({"a": "$[?(@.id =~ '.*')]"}, {"id": "1"}) == "a"
    assert (
        find_collection(
            {"a": "$[?(@.id == '1')]", "b": "$[?(@.id == '2')]"},
            {"id": "2"},
        )
        == "b"
    )
    assert (
        find_collection(
            {
                "sentinel-2-c1-l2a": "$[?(@.properties.['s2:processing_baseline'] >= '05.00')]",  # noqa: E501
                "sentinel-2-l2a-baseline-04": "$[?(@.properties.['s2:processing_baseline'] =~ '^04')]",  # noqa: E501
            },
            {"properties": {"s2:processing_baseline": "04.00"}},
        )
        == "sentinel-2-l2a-baseline-04"
    )
    assert (
        find_collection(
            {
                "sentinel-2-c1-l2a": "$[?(@.properties.['s2:processing_baseline'] >= '05.00')]",  # noqa: E501
                "sentinel-2-l2a-baseline-04": "$[?(@.properties.['s2:processing_baseline'] =~ '^04')]",  # noqa: E501
            },
            {"properties": {"s2:processing_baseline": "05.00"}},
        )
        == "sentinel-2-c1-l2a"
    )


def test_find_collection_with_jsonpath_matchers() -> None:
    """Test new list format with jsonpath matchers."""
    matchers = [
        {
            "type": "jsonpath",
            "pattern": "$[?(@.id == 'test-item')]",
            "collection_name": "test-collection",
        },
        {
            "type": "jsonpath",
            "pattern": "$[?(@.id == 'other-item')]",
            "collection_name": "other-collection",
        },
    ]

    assert find_collection(matchers, {"id": "test-item"}) == "test-collection"
    assert find_collection(matchers, {"id": "other-item"}) == "other-collection"
    assert find_collection(matchers, {"id": "unknown-item"}) is None


def test_find_collection_with_catch_all_matcher() -> None:
    """Test catch_all matcher type."""
    matchers = [{"type": "catch_all", "collection_name": "default-collection"}]

    assert find_collection(matchers, {"id": "any-item"}) == "default-collection"
    assert find_collection(matchers, {}) == "default-collection"


def test_find_collection_mixed_matcher_types() -> None:
    """Test combination of jsonpath + catch_all."""
    matchers = [
        {
            "type": "jsonpath",
            "pattern": "$[?(@.id == 'first-item')]",
            "collection_name": "first-collection",
        },
        {
            "type": "jsonpath",
            "pattern": "$[?(@.id == 'second-item')]",
            "collection_name": "second-collection",
        },
        {"type": "catch_all", "collection_name": "unknown-collection"},
    ]

    assert find_collection(matchers, {"id": "first-item"}) == "first-collection"
    assert find_collection(matchers, {"id": "second-item"}) == "second-collection"
    assert find_collection(matchers, {"id": "third-item"}) == "unknown-collection"


def test_find_collection_empty_matchers_list() -> None:
    """Test empty list returns None."""
    assert find_collection([], {"id": "any-item"}) is None


def test_find_collection_no_matchers_match() -> None:
    """Test no match returns None."""
    matchers = [
        {
            "type": "jsonpath",
            "pattern": "$[?(@.id == 'specific-item')]",
            "collection_name": "specific-collection",
        },
    ]

    assert find_collection(matchers, {"id": "different-item"}) is None
