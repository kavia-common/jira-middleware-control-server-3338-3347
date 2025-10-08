from __future__ import annotations

from fastapi import Depends

from ..clients.jira_client import JiraClient
from ..core.config import Settings, get_settings


# PUBLIC_INTERFACE
def get_app_settings() -> Settings:
    """Expose settings as dependency helper (wrapper around core.get_settings)."""
    return get_settings()


# PUBLIC_INTERFACE
async def get_jira_client(settings: Settings = Depends(get_app_settings)) -> JiraClient:
    """Yield a JiraClient with automatic open/close for each request."""
    client = JiraClient(settings)
    await client.open()
    try:
        yield client
    finally:
        await client.close()
