from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standard API error response."""
    error: str = Field(..., description="Short error type")
    message: str = Field(..., description="Human readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional extra details")


def _error_json(error: str, message: str, status_code: int, details: Optional[Dict[str, Any]] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=error, message=message, details=details).model_dump(),
    )


def install_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException):
        return _error_json("HTTPException", str(exc.detail), exc.status_code)

    @app.exception_handler(httpx.HTTPStatusError)
    async def httpx_status_error_handler(_: Request, exc: httpx.HTTPStatusError):
        logger.warning("httpx HTTPStatusError: %s", exc)
        resp = exc.response
        try:
            payload = resp.json()
        except Exception:
            payload = {"text": resp.text}
        return _error_json(
            "UpstreamHTTPError",
            f"Upstream responded with {resp.status_code}",
            resp.status_code,
            {"upstream": payload},
        )

    @app.exception_handler(httpx.RequestError)
    async def httpx_request_error_handler(_: Request, exc: httpx.RequestError):
        logger.error("httpx RequestError: %s", exc)
        return _error_json("UpstreamRequestError", "Failed to contact upstream service", 502)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        return _error_json("InternalServerError", "An unexpected error occurred", 500)
