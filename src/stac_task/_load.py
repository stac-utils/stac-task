import importlib.util
import sys

from .types import PathLikeObject


def file(path: PathLikeObject, name: str) -> None:
    """Loads a new Python module into the `stac_task.plugins` namespace.

    This can be used to load modules with tasks.

    Args:
        path: The string or Path that will be loaded
        name: The name of the module (will be prefixed with
            "stac_task.plugins.")
    """
    # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    module_name = "stac_task.plugins." + name
    if module_name in sys.modules:
        raise ValueError(f"module name is already imported: {module_name}")
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None:
        raise ValueError(
            f"could not build spec from file location: {module_name}, {path}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    if not spec.loader:
        raise ValueError(f"spec does not have a loader for module {module_name}")
    spec.loader.exec_module(module)


def plugins() -> None:
    """Load all plugins."""
    # https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/#using-package-metadata
    if sys.version_info < (3, 10):
        from importlib_metadata import entry_points
    else:
        from importlib.metadata import entry_points
    for entry_point in entry_points(group="stac_task.plugins"):
        entry_point.load()