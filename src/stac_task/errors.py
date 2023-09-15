class StacTaskError(Exception):
    """A stac-task error."""

    pass


class ExecutionError(StacTaskError):
    """An error during payload execution."""

    pass
