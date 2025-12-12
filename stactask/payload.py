import warnings
from typing import Any


class Payload(dict[str, Any]):
    def validate(self) -> None:
        _ = self.process_definition
        _ = self.workflow_options
        _ = self.task_options_dict
        _ = self.upload_options
        collection_mapping = self.collection_mapping
        _ = self.items_as_dicts
        collection_matchers = self.collection_matchers
        _ = self.collection_options

        # collection matchers and the legacy collection mapping are mutually exclusive
        if collection_matchers and collection_mapping:
            raise ValueError(
                "A payload must not contain both 'collection_matchers' and the legacy "
                "'upload_options.collections'",
            )

    @property
    def process_definition(self) -> dict[str, Any]:
        process = self.get("process", [])
        if isinstance(process, dict):
            warnings.warn(
                (
                    "'process' as a bare dictionary will be unsupported in a future "
                    "version; wrap it in a list to remove this warning"
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            return process

        if not isinstance(process, list):
            raise TypeError("unable to parse 'process': must be type list")

        if not process:
            return {}

        if not isinstance(process[0], dict):
            raise TypeError(
                "unable to parse 'process': the first element of the list must be "
                "type dict",
            )

        return process[0]

    @property
    def workflow_options(self) -> dict[str, Any]:
        workflow_options = self.process_definition.get("workflow_options", {})
        if not isinstance(workflow_options, dict):
            raise TypeError("unable to parse 'workflow_options': must be type dict")
        return workflow_options

    @property
    def task_options_dict(self) -> dict[str, dict[str, Any]]:
        task_options = self.process_definition.get("tasks", {})
        if not isinstance(task_options, dict | list):
            raise TypeError(
                "unable to parse 'tasks': must be type dict or type list (deprecated)",
            )

        if isinstance(task_options, list):
            warnings.warn(
                (
                    "'tasks' as a list of TaskConfig objects will be unsupported in a "
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
                        f"unable to parse 'parameters' for task '{name}': "
                        "must be type dict",
                    )
                options[name] = parameters
            return options

        if isinstance(task_options, dict):
            for name, options in task_options.items():
                if not isinstance(options, dict):
                    raise TypeError(
                        f"unable to parse options for task '{name}': must be type dict",
                    )
            return task_options

        return {}

    @property
    def items_as_dicts(self) -> list[dict[str, Any]]:
        features = self.get("features", [])
        if isinstance(features, list):
            return features
        raise TypeError("unable to parse 'features': must be type list")

    @property
    def upload_options(self) -> dict[str, Any]:
        upload_options = self.process_definition.get("upload_options", {})
        if isinstance(upload_options, dict):
            return upload_options
        raise TypeError("unable to parse 'upload_options': must be type dict")

    @property
    def collection_mapping(self) -> dict[str, str]:
        collection_mapping = self.upload_options.get("collections", {})
        if isinstance(collection_mapping, dict):
            warnings.warn(
                (
                    "'upload_options.collections' is deprecated and will be removed in "
                    "a future version. Use 'collection_matchers' instead."
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            return collection_mapping
        raise TypeError("unable to parse 'collections': must be type dict")

    @property
    def collection_matchers(self) -> list[dict[str, Any]]:
        matchers = self.process_definition.get("collection_matchers", [])
        if not isinstance(matchers, list):
            raise TypeError("unable to parse 'collection_matchers': must be type list")
        if not all(isinstance(matcher, dict) for matcher in matchers):
            raise TypeError(
                "unable to parse 'collection_matchers': each matcher must be type dict",
            )
        return matchers

    @property
    def collection_options(self) -> dict[str, dict[str, Any]]:
        options = self.process_definition.get("collection_options", {})
        if not isinstance(options, dict):
            raise TypeError("unable to parse 'collection_options': must be type dict")
        return options

    def get_collection_options(self, collection_name: str) -> dict[str, dict[str, Any]]:
        options = self.collection_options.get(collection_name, {})
        if not isinstance(options, dict):
            raise TypeError(
                f"unable to parse 'collection_options' for collection "
                f"'{collection_name}': must be type dict",
            )
        return options

    def get_collection_upload_options(
        self,
        collection_name: str | None,
    ) -> dict[str, Any]:
        if collection_name is None:
            return self.upload_options
        return self.get_collection_options(collection_name).get(
            "upload_options",
            self.upload_options,
        )
