from typing import Any

from pydantic import BaseModel

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


class InputModel(BaseModel):
    a: int
    b: str


class OutputModel(BaseModel):
    c: float


class SchemaTask(Task):
    name = "schema-task"
    description = "this task defines input and output models"
    version = "0.2.0"

    input_model = InputModel
    output_model = OutputModel

    def process(self, **kwargs: Any) -> list[dict[str, Any]]:
        return [OutputModel(c=2.7)]
