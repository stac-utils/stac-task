import warnings
from typing import Any


class Payload(dict[str, Any]):
    def validate(self) -> None:
        self.process_definition
        self.workflow_options
        self.task_options_dict
        self.upload_options
        self.collection_mapping
        self.items_as_dicts

    @property
    def process_definition(self) -> dict[str, Any]:
        process = self.get("process", [])
        if isinstance(process, dict):
            warnings.warn(
                (
                    "`process` as a bare dictionary will be unsupported in a future "
                    "version; wrap it in a list to remove this warning"
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            return process

        if not isinstance(process, list):
            raise TypeError("unable to parse `process`: must be type list")

        if not process:
            return {}

        if not isinstance(process[0], dict):
            raise TypeError(
                (
                    "unable to parse `process`: the first element of the list must be "
                    "a dictionary"
                )
            )

        return process[0]

    @property
    def workflow_options(self) -> dict[str, Any]:
        workflow_options = self.process_definition.get("workflow_options", {})
        if not isinstance(workflow_options, dict):
            raise TypeError("unable to parse `workflow_options`: must be type dict")
        return workflow_options

    @property
    def task_options_dict(self) -> dict[str, dict[str, Any]]:
        task_options = self.process_definition.get("tasks", {})
        if not isinstance(task_options, (dict, list)):
            raise TypeError(
                "unable to parse `tasks`: must be type dict or type list (deprecated)"
            )

        if isinstance(task_options, list):
            warnings.warn(
                (
                    "`tasks` as a list of TaskConfig objects will be unsupported in a "
                    "future version; use a dictionary of task options to remove this "
                    "warning"
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            options: dict[str, dict[str, Any]] = {}
            for cfg in task_options:
                name = cfg["name"]
                parameters = cfg.get("parameters", {})
                if not isinstance(parameters, dict):
                    raise TypeError(
                        f"unable to parse 'parameters' for task '{name}': must be "
                        "type dict"
                    )
                options[name] = parameters
            return options

        if isinstance(task_options, dict):
            for name, options in task_options.items():
                if not isinstance(options, dict):
                    raise TypeError(
                        f"unable to parse options for task '{name}': must be type dict"
                    )
            return task_options

    @property
    def upload_options(self) -> dict[str, Any]:
        # self.payload.global_upload_options
        upload_options = self.process_definition.get("upload_options", {})
        if isinstance(upload_options, dict):
            return upload_options
        else:
            raise ValueError(f"upload_options is not a dict: {type(upload_options)}")

    @property
    def collection_mapping(self) -> dict[str, str]:
        collection_mapping = self.upload_options.get("collections", {})
        if isinstance(collection_mapping, dict):
            return collection_mapping
        else:
            raise ValueError(f"collections is not a dict: {type(collection_mapping)}")

    @property
    def items_as_dicts(self) -> list[dict[str, Any]]:
        features = self.get("features", [])
        if isinstance(features, list):
            return features
        else:
            raise ValueError(f"features is not a list: {type(features)}")
