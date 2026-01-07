from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    _LoggerAdapter = logging.LoggerAdapter[logging.Logger]  # pragma: no cover
else:
    _LoggerAdapter = logging.LoggerAdapter


class TaskLoggerAdapter(_LoggerAdapter):
    def __init__(
        self,
        logger: logging.Logger,
        payload_id: str | None,
        aws_request_id: str | None = None,
    ) -> None:
        super().__init__(logger, {})
        self.payload_id = payload_id
        self.aws_request_id = aws_request_id

    def process(self, msg: str, kwargs: Any) -> tuple[str, Any]:
        if self.payload_id is not None and self.aws_request_id is not None:
            prefix = f"{self.payload_id}:{self.aws_request_id}"
        elif self.payload_id is not None:
            prefix = self.payload_id
        elif self.aws_request_id is not None:
            prefix = self.aws_request_id
        else:
            prefix = ""

        if prefix:
            return f"{prefix}:{msg}", kwargs
        return msg, kwargs
