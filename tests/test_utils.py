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


def test_find_collection() -> None:
    assert find_collection({"a": "$[?(@.id =~ '.*')]"}, {"id": "1"}) == "a"
    assert (
        find_collection(
            {"a": "$[?(@.id == '1')]", "b": "$[?(@.id == '2')]"}, {"id": "2"}
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
