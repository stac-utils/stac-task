from typing import Any

from stactask import Task
from stactask.exceptions import FailedValidation


class NothingTask(Task):
    name = "nothing-task"
    description = "this task does nothing"

    def process(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self.items_as_dicts


class FailValidateTask(Task):
    name = "failvalidation-task"
    description = "this task always fails validation"

    def validate(self) -> bool:
        if self._payload:
            raise FailedValidation("Extra context about what went wrong")
        return True

    def process(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self.items_as_dicts


class DerivedItemTask(Task):
    name = "derived-item-task"
    description = "this task creates a derived item"

    def process(self, **kwargs: Any) -> list[dict[str, Any]]:
        assert kwargs["parameter"] == "value"
        return [self.create_item_from_item(self.items_as_dicts[0])]
