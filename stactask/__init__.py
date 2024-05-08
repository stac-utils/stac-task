from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("stactask")
except PackageNotFoundError:
    # package is not installed
    pass

from .config import DownloadConfig
from .task import Task

__all__ = ["Task", "DownloadConfig"]
