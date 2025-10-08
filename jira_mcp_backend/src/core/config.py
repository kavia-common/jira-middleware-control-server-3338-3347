from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Uses Pydantic BaseSettings to load configuration with validation and defaults where appropriate.
    """

    # App
    APP_NAME: str = Field(default="JIRA MCP Server", description="Application display name")
    APP_ENV: str = Field(default="development", description="Application environment")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    ALLOW_ORIGINS: List[str] = Field(
        default=["*"], description="CORS allowed origins list"
    )

    # Auth
    AUTH_STRATEGY: str = Field(
        default="api_key", description="Authentication strategy: 'api_key' or 'jwt'"
    )
    API_KEY_HEADER_NAME: str = Field(
        default="X-API-Key", description="Header name used to pass API key"
    )
    API_KEYS: List[str] = Field(
        default=[], description="List of allowed API keys for api_key strategy"
    )

    # Optional JWT config (stub/optional)
    JWT_JWKS_URL: Optional[AnyHttpUrl] = Field(
        default=None, description="JWKS URL for JWT validation"
    )
    JWT_ISSUER: Optional[str] = Field(default=None, description="Expected JWT issuer")
    JWT_AUDIENCE: Optional[str] = Field(default=None, description="Expected JWT audience")

    # JIRA
    JIRA_BASE_URL: AnyHttpUrl = Field(
        ..., description="Base URL for JIRA instance, e.g., https://your-domain.atlassian.net"
    )
    JIRA_EMAIL: str = Field(..., description="JIRA account email for API auth")
    JIRA_API_TOKEN: str = Field(..., description="JIRA API token for API auth")
    JIRA_CLOUD: bool = Field(default=True, description="Is the JIRA instance cloud-based")

    # HTTP
    REQUEST_TIMEOUT_SECONDS: float = Field(
        default=30.0, description="Default request timeout in seconds for outbound HTTP"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @model_validator(mode="after")
    def _validate_auth(self) -> "Settings":
        strategy = (self.AUTH_STRATEGY or "").lower().strip()
        if strategy not in {"api_key", "jwt"}:
            raise ValueError("AUTH_STRATEGY must be either 'api_key' or 'jwt'")
        if strategy == "api_key":
            if not self.API_KEYS:
                raise ValueError("When AUTH_STRATEGY=api_key, API_KEYS must contain at least one key")
        if strategy == "jwt":
            if not (self.JWT_JWKS_URL and self.JWT_ISSUER and self.JWT_AUDIENCE):
                raise ValueError(
                    "When AUTH_STRATEGY=jwt, JWT_JWKS_URL, JWT_ISSUER, and JWT_AUDIENCE must be set"
                )
        return self


# PUBLIC_INTERFACE
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
