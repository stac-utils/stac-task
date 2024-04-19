from typing import Any, Dict, Optional

from jsonpath_ng.ext import parser


def stac_jsonpath_match(item: Dict[str, Any], expr: str) -> bool:
    """Match jsonpath expression against STAC JSON.
       Use https://jsonpath.com to experiment with JSONpath
        and https://regex101.com to experiment with regex

    Args:
        item (Dict): A STAC Item
        expr (str): A valid JSONPath expression

    Raises:
        err: Invalid inputs

    Returns:
        Boolean: Returns True if the jsonpath expression matches the STAC Item JSON
    """
    return len([x.value for x in parser.parse(expr).find([item])]) == 1


def find_collection(
    collection_mapping: Dict[str, str], item: Dict[str, Any]
) -> Optional[str]:
    """Find the collection for a given STAC Item represented as a dictionary from a
       dictionary of collection names to JSONPath expressions.

    Args:
        collection_mapping (Dict): A dictionary of collection names to JSONPath
            expressions.
        item (Dict): A STAC Item

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
