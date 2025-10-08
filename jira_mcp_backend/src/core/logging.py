from __future__ import annotations

import logging
import sys
import time
from typing import Callable

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging(level: str = "INFO") -> None:
    """Configure application-wide logging."""
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(level.upper())


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging with latency."""

    async def dispatch(self, request: Request, call_next: Callable):
        logger = logging.getLogger("request")
        start = time.time()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration = (time.time() - start) * 1000.0
            logger.info(
                "%s %s -> %s (%.2f ms)",
                request.method,
                request.url.path,
                getattr(response, "status_code", "n/a"),
                duration,
            )


def install_request_logging(app: FastAPI) -> None:
    """Attach request logging middleware to the app."""
    app.add_middleware(RequestLoggingMiddleware)
