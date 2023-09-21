"""Test fixture for testing the -f flag for the CLI."""

import stac_task
from stac_task import Anything, OneToOneTask


class PassthroughTask(OneToOneTask[Anything, Anything]):
    def process_one_to_one(self, input: Anything) -> Anything:
        return input


stac_task.register_task("passthrough", PassthroughTask)
