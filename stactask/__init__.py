from .config import DownloadConfig
from .payload import Payload
from .task import Task

try:
    from .__version__ import __version__, __version_tuple__
except ImportError:
    __version__ = "0.0.0"
    __version_tuple__ = ("0", "0", "0")

__all__ = [
    "__version__",
    "__version_tuple__",
    "Task",
    "Payload",
    "DownloadConfig",
]
