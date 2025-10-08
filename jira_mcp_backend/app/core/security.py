from typing import Optional

from fastapi import Depends, HTTPException, Request, status

from app.core.config import AppSettings, get_settings


# PUBLIC_INTERFACE
def get_auth_dependency(settings: Optional[AppSettings] = None):
    """Dependency factory for Bearer token validation using env AUTH_TOKEN.

    Raises HTTP 401 if Authorization header missing or invalid.
    """

    settings = settings or get_settings()

    async def require_bearer_auth(request: Request):
        expected = settings.AUTH_TOKEN
        if not expected:
            # If not configured, we keep the service protected by failing fast.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "auth_not_configured", "message": "AUTH_TOKEN is not configured on server."},
            )
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or token != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "unauthorized", "message": "Invalid or missing bearer token."},
            )
        return None

    return Depends(require_bearer_auth)
