from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    _LoggerAdapter = logging.LoggerAdapter[logging.Logger]  # pragma: no cover
else:
    _LoggerAdapter = logging.LoggerAdapter


class TaskLoggerAdapter(_LoggerAdapter):
    def __init__(self, logger: logging.Logger, prefix: Optional[str]) -> None:
        super().__init__(logger, {})
        self.prefix = prefix

    def process(self, msg: str, kwargs: Any) -> tuple[str, Any]:
        if self.prefix is not None:
            return f"[{self.prefix}] {msg}", kwargs
        else:
            return msg, kwargs
