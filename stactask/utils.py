from typing import Any, Optional

from jsonpath_ng.ext import parser


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


def find_collection(
    collection_mapping: dict[str, str], item: dict[str, Any]
) -> Optional[str]:
    """Find the collection for a given STAC Item represented as a dictionary from a
       dictionary of collection names to JSONPath expressions.

    Args:
        collection_mapping (dict): A dictionary of collection names to JSONPath
            expressions.
        item (dict): A STAC Item

    Returns:
        Optional[str]: Returns None if no JSONPath expression matches, returns a
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
