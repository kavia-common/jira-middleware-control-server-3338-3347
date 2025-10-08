import logging
import sys



class RequestIDFilter(logging.Filter):
    """Inject request_id if present in record.extra"""

    def filter(self, record: logging.LogRecord) -> bool:
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
