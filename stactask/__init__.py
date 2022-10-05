# flake8: noqa

import pkg_resources

__version__ = pkg_resources.get_distribution(__package__).version

from .task import Task
