from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # PUBLIC_INTERFACE
    model_config = SettingsConfigDict(env_prefix="", env_file=None, extra="ignore")

    # Auth
    AUTH_TOKEN: Optional[str] = Field(
        default=None,
        description="Static Bearer token required in Authorization header for client requests.",
    )

    # JIRA
    JIRA_BASE_URL: Optional[str] = Field(default=None, description="Base URL for JIRA REST API, e.g., https://your-domain.atlassian.net")
    JIRA_EMAIL: Optional[str] = Field(default=None, description="JIRA account email used for API token authentication")
    JIRA_API_TOKEN: Optional[str] = Field(default=None, description="JIRA API token for the specified email")
    JIRA_CLOUD_INSTANCE: bool = Field(default=True, description="Whether this is an Atlassian Cloud instance")

    # CORS
    CORS_ALLOW_ORIGINS: List[str] = Field(
        default_factory=lambda: ["*"],
        description="List of allowed origins for CORS",
    )

    # Server
    PORT: int = Field(default=3001, description="Preview server port (handled externally)")
    DEBUG: bool = Field(default=False, description="Enable debug logging")


# PUBLIC_INTERFACE
@lru_cache
def get_settings() -> AppSettings:
    """Returns cached application settings from environment."""
    return AppSettings()
