import base64
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class JiraConfigError(RuntimeError):
    """Raised when JIRA configuration is missing or invalid."""


class JiraClient:
    """Thin JIRA REST API client abstraction with safe error handling."""

    def __init__(
        self,
        base_url: Optional[str],
        email: Optional[str],
        api_token: Optional[str],
        cloud_instance: bool = True,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self.email = email
        self.api_token = api_token
        self.cloud_instance = cloud_instance
        self.timeout = timeout

    def _ensure_configured(self) -> None:
        if not (self.base_url and self.email and self.api_token):
            raise JiraConfigError(
                "JIRA is not configured. Please set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN."
            )

    def _auth_headers(self) -> Dict[str, str]:
        token = base64.b64encode(f"{self.email}:{self.api_token}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout)

    # PUBLIC_INTERFACE
    async def get_issue(self, key: str) -> Optional[Dict[str, Any]]:
        """Fetch a JIRA issue by key. Returns dict or None if not found."""
        self._ensure_configured()
        url = f"{self.base_url}/rest/api/3/issue/{key}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self._auth_headers())
            if resp.status_code == 404:
                return None
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.warning("JIRA get_issue error: %s | body=%s", e, resp.text)
                raise
            return resp.json()

    # PUBLIC_INTERFACE
    async def search_issues(
        self,
        jql: str,
        start_at: int = 0,
        max_results: int = 50,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute a JQL search and return the raw response JSON."""
        self._ensure_configured()
        url = f"{self.base_url}/rest/api/3/search"
        payload: Dict[str, Any] = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
        }
        if fields is not None:
            payload["fields"] = fields
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=self._auth_headers(), json=payload)
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.warning("JIRA search error: %s | body=%s", e, resp.text)
                raise
            return resp.json()

    # PUBLIC_INTERFACE
    async def create_issue(self, project_key: str, summary: str, issue_type: str = "Task", fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a JIRA issue. Basic stub for future extension."""
        self._ensure_configured()
        url = f"{self.base_url}/rest/api/3/issue"
        body_fields: Dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }
        if fields:
            body_fields.update(fields)
        payload = {"fields": body_fields}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=self._auth_headers(), json=payload)
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.warning("JIRA create_issue error: %s | body=%s", e, resp.text)
                raise
            return resp.json()
