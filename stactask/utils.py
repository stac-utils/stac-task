from typing import Dict

from jsonpath_ng.ext import parser


def stac_jsonpath_match(item: Dict, expr: str) -> bool:
    """Match jsonpath expression against STAC JSON.
       Use https://jsonpath.herokuapp.com/ to experiment with JSONpath
        and https://regex101.com/ to experiment with regex

    Args:
        item (Dict): A STAC Item
        expr (str): A valid JSONPath expression

    Raises:
        err: Invalid inputs

    Returns:
        Boolean: Returns True if the jsonpath expression matches the STAC Item JSON
    """
    result = [x.value for x in parser.parse(expr).find([item])]
    if len(result) == 1:
        return True
    else:
        return False
