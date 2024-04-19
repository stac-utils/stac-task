from __future__ import annotations

import logging
from typing import Any, Optional


class TaskLoggerAdapter(logging.LoggerAdapter):  # type: ignore
    def __init__(self, logger: logging.Logger, prefix: Optional[str]) -> None:
        super().__init__(logger, {})
        self.prefix = prefix

    def process(self, msg: str, kwargs: Any) -> tuple[str, Any]:
        if self.prefix is not None:
            return f"[{self.prefix}] {msg}", kwargs
        else:
            return msg, kwargs
