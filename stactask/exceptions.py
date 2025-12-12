import pystac


class InvalidInput(Exception):  # noqa: N818
    """Exception class for when processing fails due to invalid input

    Args:
        Exception (Exception): Base class
    """

    pass


class FailedValidation(Exception):  # noqa: N818
    """Exception class thrown when input payload does not validate"""

    pass


class StorageReadError(Exception):
    """Exception class for cloud storage object access errors"""


class PystacConversionError(pystac.errors.STACError):
    """Generic exception class for pystac conversion errors."""
