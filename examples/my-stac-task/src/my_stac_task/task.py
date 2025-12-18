from typing import Any

from stactask import Task

from .processor import process_item


class MyStacTask(Task):
    name = "my-stac-task"
    description = "An example STAC Task"

    def validate(self) -> None:
        """Custom validation logic for the task.

        Bespoke validation task-specific parameters can be implemented here.
        This method is called by the parent class during task initialization.
        """
        return True

    def process(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Core task processing logic.

        This method is called by the parent class to perform the main work of the task.
        All business logic should be implemented here.
        """

        # this block is specific to the my-stac-task tests and can be removed as-needed
        # during task customization
        if "invalid" in self.process_definition.get("id", ""):
            raise Exception("invalid")

        # example processing: create and process a STAC Item
        updated_payload = process_item(self.payload)

        # return a list of Items
        return updated_payload.get("features", [])


def lambda_handler(event: dict, context: dict = {}):
    return MyStacTask.handler(payload=event)


if __name__ == "__main__":
    MyStacTask.cli()
