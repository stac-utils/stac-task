class InvalidInput(Exception):  # noqa: N818
    """Exception class for when processing fails due to invalid input

    Args:
        Exception (Exception): Base class
    """

    pass


class FailedValidation(Exception):  # noqa: N818
    """Exception class thrown when input payload does not validate"""

    pass
