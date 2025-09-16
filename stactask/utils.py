from enum import Enum
from typing import Any

from jsonpath_ng.ext import parser


class MatcherType(str, Enum):
    JSONPATH = "jsonpath"
    CATCH_ALL = "catch_all"


def stac_jsonpath_match(item: dict[str, Any], expr: str) -> bool:
    """Match jsonpath expression against STAC JSON.
       Use https://jsonpath.com to experiment with JSONpath
        and https://regex101.com to experiment with regex

    Args:
        item (dict): A STAC Item represented as a dict
        expr (str): A valid JSONPath expression

    Raises:
        err: Invalid inputs

    Returns:
        Boolean: Returns True if the jsonpath expression matches the STAC Item JSON
    """
    return len([x.value for x in parser.parse(expr).find([item])]) == 1


def _find_collection_from_mapping(
    collection_mapping: dict[str, str],
    item: dict[str, Any],
) -> str | None:
    """Find the collection for a given STAC Item represented as a dictionary from a
       dictionary of collection names to JSONPath expressions.

    Args:
        collection_mapping (dict): A dictionary of collection names to JSONPath
            expressions.
        item (dict): A STAC Item

    Returns:
        str | None: Returns None if no JSONPath expression matches, returns a
        collection name if one does
    """
    return next(
        (
            c
            for c, expr in collection_mapping.items()
            if stac_jsonpath_match(item, expr)
        ),
        None,
    )


def _find_collection_from_matchers(
    collection_matchers: list[dict[str, Any]],
    item: dict[str, Any],
) -> str | None:
    """Find the collection for a given STAC Item represented as a dictionary from a
    list of collection matcher dictionaries.

    Args:
        collection_matchers: List of matcher dictionaries with 'type',
            'collection_name', and 'pattern' (except the 'catch_all' matcher) fields.
        item: A STAC Item represented as a dictionary.

    Returns:
        str | None: Returns None if no matcher matches, returns a collection
        name if one does.
    """
    for matcher in collection_matchers:
        matcher_type = matcher["type"]
        collection_name: str = matcher["collection_name"]

        if matcher_type == MatcherType.JSONPATH:
            if stac_jsonpath_match(item, matcher["pattern"]):
                return collection_name
        elif matcher_type == MatcherType.CATCH_ALL:
            return collection_name
        else:
            raise ValueError(f"Unknown matcher type: {matcher_type}")

    return None


def find_collection(
    collection_config: dict[str, str] | list[dict[str, Any]],
    item: dict[str, Any],
) -> str | None:
    """Find the collection for a given STAC Item from either a list of collection
       matchers or a legacy collection mapping.

    Args:
        collection_config: Either a list of collection matcher dictionaries
            (new format) or a dictionary of collection names to JSONPath expressions
            (legacy format).
        item (dict): A STAC Item represented as a dictionary.

    Returns:
        str | None: Returns None if no match is found, returns a collection name if
        one is found.
    """
    if not collection_config:
        return None

    if isinstance(collection_config, dict):
        return _find_collection_from_mapping(collection_config, item)
    if isinstance(collection_config, list):
        return _find_collection_from_matchers(collection_config, item)
    raise TypeError(
        f"Unsupported collection config type: {type(collection_config)}. "
        "Expected dict or list of dicts.",
    )
