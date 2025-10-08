import logging
import sys
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional


class RequestIDFilter(logging.Filter):
    """Inject request_id if present in record.extra"""

    def filter(self, record: logging.LogRecord) -> bool:
        # ensure request_id attribute exists to satisfy formatter even if not provided
        if not hasattr(record, "request_id"):
            record.request_id = getattr(record, "request_id", None)
        return True


logger = logging.getLogger("jira_mcp")


# PUBLIC_INTERFACE
def configure_logging(level: str = "INFO") -> None:
    """
    Configure structured logging for the application and uvicorn loggers.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s request_id=%(request_id)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIDFilter())

    root.setLevel(log_level)
    root.addHandler(handler)

    # align uvicorn loggers
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.setLevel(log_level)
        for h in list(uv_logger.handlers):
            uv_logger.removeHandler(h)
        uv_logger.addHandler(handler)


# PUBLIC_INTERFACE
def log_debug_with_context(message: str, request_id: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> None:
    """
    Emit a debug-level log with request_id and arbitrary context fields.
    """
    data = {"request_id": request_id}
    if extra:
        data.update(extra)
    logger.debug(message, extra=data)


# PUBLIC_INTERFACE
@contextmanager
def timed_log_debug(message: str, request_id: Optional[str] = None, extra: Optional[Dict[str, Any]] = None):
    """
    Context manager to time a code block and log duration at debug level.

    Usage:
        with timed_log_debug("jira_request", request_id=req_id, extra={"method": "GET", "path": "/issue"}):
            # do work
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        data = {"request_id": request_id, "duration_ms": duration_ms}
        if extra:
            data.update(extra)
        logger.debug(message, extra=data)
