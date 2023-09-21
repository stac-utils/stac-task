from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict
from stac_task import Anything, Nothing, OneToOneTask


class PassthroughTask(OneToOneTask[Anything, Anything]):
    def process_one_to_one(self, input: Anything) -> Anything:
        return input


class TheMeaningOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    the_meaning: int


class TheMeaningTask(OneToOneTask[Nothing, TheMeaningOutput]):
    input = Nothing
    output = TheMeaningOutput

    foo: Optional[bool] = None

    def process_one_to_one(self, input: Nothing) -> TheMeaningOutput:
        fields: Dict[str, Any] = {"the_meaning": 42}
        if self.foo:
            fields["foo"] = "bar"
        return TheMeaningOutput(**fields)
