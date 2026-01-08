import io
import logging

from stactask.logging import TaskLoggerAdapter


def make_adapter(
    payload_id: str | None,
    aws_request_id: str | None,
) -> tuple[TaskLoggerAdapter, io.StringIO]:
    stream = io.StringIO()
    logger = logging.getLogger("test-logger-name")
    logger.handlers.clear()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    adapter = TaskLoggerAdapter(
        logger=logger,
        payload_id=payload_id,
        aws_request_id=aws_request_id,
    )
    return adapter, stream


def test_formats_with_both_ids() -> None:
    adapter, stream = make_adapter("test-payload-id", "test-request-id")
    adapter.info("Test log message")
    assert (
        stream.getvalue().strip()
        == "INFO:test-logger-name:test-payload-id:test-request-id:Test log message"
    )


def test_formats_with_payload_only() -> None:
    adapter, stream = make_adapter("test-payload-id", None)
    adapter.info("Test log message")
    assert (
        stream.getvalue().strip()
        == "INFO:test-logger-name:test-payload-id:Test log message"
    )


def test_formats_with_request_only() -> None:
    adapter, stream = make_adapter(None, "test-request-id")
    adapter.info("Test log message")
    assert (
        stream.getvalue().strip()
        == "INFO:test-logger-name:test-request-id:Test log message"
    )


def test_formats_without_ids() -> None:
    adapter, stream = make_adapter(None, None)
    adapter.info("Test log message")
    assert stream.getvalue().strip() == "INFO:test-logger-name:Test log message"
