from typing import Any, Dict, List

from stactask import Task


class NothingTask(Task):
    name = "nothing-task"
    description = "this task does nothing"

    def process(self, **kwargs: Any) -> List[Dict[str, Any]]:
        return self.items_as_dicts


class FailValidateTask(Task):
    name = "failvalidation-task"
    description = "this task always fails validation"

    @classmethod
    def validate(self, payload: Dict[str, Any]) -> bool:
        return False

    def process(self, **kwargs: Any) -> List[Dict[str, Any]]:
        return self.items_as_dicts


class DerivedItemTask(Task):
    name = "derived-item-task"
    description = "this task creates a derived item"

    def process(self, **kwargs: Any) -> List[Dict[str, Any]]:
        assert kwargs["parameter"] == "value"
        return [self.create_item_from_item(self.items_as_dicts[0])]
