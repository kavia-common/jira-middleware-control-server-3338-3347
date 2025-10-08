from __future__ import annotations

import base64
from typing import Any, Dict, Optional

import httpx

from ..core.config import Settings


class JiraClient:
    """
    Async HTTP client for JIRA REST API (Cloud or Server) using basic auth (email + API token).
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = str(settings.JIRA_BASE_URL).rstrip("/")
        self.timeout = httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS)
        self._client: Optional[httpx.AsyncClient] = None

    async def open(self) -> None:
        if self._client is None:
            auth_header = self._basic_auth_header(self.settings.JIRA_EMAIL, self.settings.JIRA_API_TOKEN)
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": auth_header, "Accept": "application/json", "Content-Type": "application/json"},
                timeout=self.timeout,
            )

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _basic_auth_header(self, username: str, token: str) -> str:
        raw = f"{username}:{token}".encode("utf-8")
        b64 = base64.b64encode(raw).decode("ascii")
        return f"Basic {b64}"

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            await self.open()
        assert self._client is not None
        return self._client

    async def get_issue(self, issue_key: str, fields: Optional[str] = None) -> Dict[str, Any]:
        client = await self._ensure_client()
        params = {"fields": fields} if fields else None
        resp = await client.get(f"/rest/api/3/issue/{issue_key}", params=params)
        resp.raise_for_status()
        return resp.json()

    async def create_issue(self, project_key: str, summary: str, issuetype_name: str, description: Optional[str] = None) -> Dict[str, Any]:
        client = await self._ensure_client()
        payload: Dict[str, Any] = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issuetype_name},
            }
        }
        if description is not None:
            payload["fields"]["description"] = description
        resp = await client.post("/rest/api/3/issue", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def transition_issue(self, issue_key: str, transition_id: str) -> None:
        client = await self._ensure_client()
        payload = {"transition": {"id": transition_id}}
        resp = await client.post(f"/rest/api/3/issue/{issue_key}/transitions", json=payload)
        resp.raise_for_status()
        return None

    async def add_comment(self, issue_key: str, body: str) -> Dict[str, Any]:
        client = await self._ensure_client()
        payload = {"body": body}
        resp = await client.post(f"/rest/api/3/issue/{issue_key}/comment", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def search(self, jql: str, start_at: int = 0, max_results: int = 50, fields: Optional[list[str]] = None) -> Dict[str, Any]:
        client = await self._ensure_client()
        payload: Dict[str, Any] = {"jql": jql, "startAt": start_at, "maxResults": max_results}
        if fields is not None:
            payload["fields"] = fields
        resp = await client.post("/rest/api/3/search", json=payload)
        resp.raise_for_status()
        return resp.json()
