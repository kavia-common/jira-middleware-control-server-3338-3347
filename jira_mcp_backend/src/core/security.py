from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader
from jose import jwt  # noqa: F401
from pydantic import BaseModel

from .config import Settings, get_settings


class AuthenticatedClient(BaseModel):
    """Represents the authenticated client principal."""
    subject: str
    strategy: str
    api_key_last4: Optional[str] = None


def _api_key_dependency(settings: Settings) -> APIKeyHeader:
    return APIKeyHeader(name=settings.API_KEY_HEADER_NAME, auto_error=False)


# PUBLIC_INTERFACE
async def get_current_client(
    request: Request,
    settings: Settings = Depends(get_settings),
    api_key_header: Optional[str] = Depends(lambda settings=Depends(get_settings): _api_key_dependency(settings)),
) -> AuthenticatedClient:
    """
    Authenticate the client based on configured strategy.

    When AUTH_STRATEGY=api_key:
      - Expects header {API_KEY_HEADER_NAME}: <key>
      - Validates against settings.API_KEYS

    When AUTH_STRATEGY=jwt:
      - Placeholder for JWT validation (JWKS). Raises NotImplementedError unless fully configured.
    """
    strategy = settings.AUTH_STRATEGY.lower().strip()

    if strategy == "api_key":
        # Header value is retrieved via dependency created with settings
        header_name = settings.API_KEY_HEADER_NAME
        provided = request.headers.get(header_name)
        if not provided or provided not in set(settings.API_KEYS):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
            )
        return AuthenticatedClient(
            subject="api_key_client",
            strategy="api_key",
            api_key_last4=provided[-4:] if len(provided) >= 4 else provided,
        )

    if strategy == "jwt":
        # Optional stub; clearly indicate not implemented unless configured with proper libs.
        # Implementation would fetch JWKS, verify signature, issuer, audience, etc.
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="JWT authentication is not implemented in this build.",
        )

    # Should not reach here due to settings validation
    raise HTTPException(status_code=500, detail="Authentication strategy misconfigured")
