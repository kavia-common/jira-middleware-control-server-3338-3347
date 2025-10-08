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

    # JIRA client behavior
    JIRA_TIMEOUT_SECONDS: float = Field(default=15.0, description="HTTP client timeout for JIRA API calls (seconds)")
    JIRA_RETRY_MAX_ATTEMPTS: int = Field(default=3, description="Max retry attempts for transient JIRA errors (including 429/5xx)")
    JIRA_RETRY_BACKOFF_BASE: float = Field(default=0.5, description="Base backoff in seconds for exponential retry")

    # JIRA custom field names (display names)
    JIRA_STORY_POINTS_FIELD_NAME: str = Field(default="Story points", description="Display name for Story Points custom field")
    JIRA_EPIC_LINK_FIELD_NAME: str = Field(default="Epic Link", description="Display name for Epic Link custom field")
    JIRA_EPIC_NAME_FIELD_NAME: str = Field(default="Epic Name", description="Display name for Epic Name custom field")

    # Defaults for convenience
    DEFAULT_TIMEZONE: str = Field(default="UTC", description="Default timezone for sprint date interpretation")
    DEFAULT_BOARD_ID: Optional[int] = Field(default=None, description="Optional default Agile board id")

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

        # Optional DEFAULT_BOARD_ID: allow int or blank
        default_board_id_raw = env.get("DEFAULT_BOARD_ID")
        if default_board_id_raw is not None and default_board_id_raw.strip() != "":
            try:
                data["DEFAULT_BOARD_ID"] = int(default_board_id_raw)
            except ValueError:
                # Leave as None if invalid; logging left to startup validation paths if needed
                data["DEFAULT_BOARD_ID"] = None

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
