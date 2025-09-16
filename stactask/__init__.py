from contextlib import suppress
from importlib.metadata import PackageNotFoundError, version

with suppress(PackageNotFoundError):
    __version__ = version("stactask")

from .config import DownloadConfig
from .payload import Payload
from .task import Task

__all__ = ["Task", "Payload", "DownloadConfig"]
