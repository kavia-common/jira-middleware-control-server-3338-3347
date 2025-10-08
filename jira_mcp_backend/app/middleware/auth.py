from __future__ import annotations

from typing import Iterable, Optional

from fastapi import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.utils.logging import logger


def _authorized(api_keys: Iterable[str], request: Request) -> bool:
    """
    Returns True if the request contains a valid API key in either X-API-KEY header
    or Authorization: Bearer <token>.
    """
    if not api_keys:
        # If no API keys configured, deny all except health/root (handled by caller)
        return False

    # Header X-API-KEY
    x_api_key: Optional[str] = request.headers.get("X-API-KEY")
    if x_api_key and x_api_key in api_keys:
        return True

    # Authorization: Bearer <token>
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[len("Bearer ") :].strip()
        if token and token in api_keys:
            return True

    return False


async def api_key_auth_middleware(request: Request, call_next):
    """
    PUBLIC_INTERFACE
    Simple API Key authentication. Validates X-API-KEY header or Bearer token against APP_API_KEYS.
    Skips authentication for "/" and "/health".
    """
    path = request.url.path
    if path in ("/", "/health"):
        return await call_next(request)

    settings = get_settings()
    if _authorized(settings.APP_API_KEYS, request):
        return await call_next(request)

    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        "unauthorized_request",
        extra={"path": path, "method": request.method, "request_id": request_id},
    )
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": "unauthorized",
                "message": "Missing or invalid API key.",
                "details": None,
            },
            "request_id": request_id,
        },
    )
