from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    PUBLIC_INTERFACE
    Application configuration loaded from environment variables using pydantic-settings.
    """

    # JIRA config
    JIRA_BASE_URL: Optional[str] = Field(default=None, description="Base URL for JIRA REST API")
    JIRA_EMAIL: Optional[str] = Field(default=None, description="JIRA account email")
    JIRA_API_TOKEN: Optional[str] = Field(default=None, description="JIRA API token")
    JIRA_CLOUD_SITE: Optional[str] = Field(default=None, description="Cloud site key, e.g., yoursite")

    # App config
    APP_ENV: str = Field(default="development", description="Application environment")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level, e.g., DEBUG, INFO, WARNING")
    APP_CORS_ORIGINS: List[str] | None = Field(
        default=None, description="Comma-separated list of allowed CORS origins"
    )
    APP_API_KEYS: List[str] = Field(
        default_factory=list, description="Comma-separated list of accepted API keys"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def __init__(self, **data):
        # Pre-process comma-separated fields
        env = os.environ

        api_keys_raw = env.get("APP_API_KEYS")
        if api_keys_raw:
            data["APP_API_KEYS"] = [v.strip() for v in api_keys_raw.split(",") if v.strip()]

        cors_raw = env.get("APP_CORS_ORIGINS")
        if cors_raw:
            data["APP_CORS_ORIGINS"] = [v.strip() for v in cors_raw.split(",") if v.strip()]
        super().__init__(**data)

    @property
    def jira_base_url(self) -> Optional[str]:
        """Resolve base URL using JIRA_BASE_URL or JIRA_CLOUD_SITE."""
        if self.JIRA_BASE_URL:
            return self.JIRA_BASE_URL.rstrip("/")
        if self.JIRA_CLOUD_SITE:
            return f"https://{self.JIRA_CLOUD_SITE}.atlassian.net"
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    PUBLIC_INTERFACE
    Returns a singleton settings instance loaded from environment variables.
    """
    return Settings()
