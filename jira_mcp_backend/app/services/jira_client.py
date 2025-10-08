from __future__ import annotations

import asyncio
import base64
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings



class JiraClientError(Exception):
    """Represents an error interacting with the JIRA API."""

    def __init__(self, message: str, status_code: int = 502, details: Any | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class JiraClient:
    """
    PUBLIC_INTERFACE
    Async JIRA API client with basic auth and exponential backoff retries for 5xx errors.
    """

    def __init__(self, base_url: str, email: str, api_token: str, timeout: float = 15.0) -> None:
        if not base_url or not email or not api_token:
            raise ValueError("Missing JIRA configuration for client initialization.")
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Basic {self._basic_token()}",
            }
            self._client = httpx.AsyncClient(base_url=f"{self.base_url}/rest/api/3", headers=headers, timeout=self.timeout)
        return self._client

    def _basic_token(self) -> str:
        token = base64.b64encode(f"{self.email}:{self.api_token}".encode("utf-8")).decode("utf-8")
        return token

    async def _request_with_retries(self, method: str, url: str, **kwargs) -> httpx.Response:
        max_attempts = 3
        backoff_base = 0.5
        last_exc: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                client = await self._get_client()
                resp = await client.request(method, url, **kwargs)
                if 500 <= resp.status_code < 600:
                    # Server error, retry
                    raise JiraClientError(
                        message=f"JIRA server error {resp.status_code}",
                        status_code=502,
                        details=await self._safe_response_text(resp),
                    )
                return resp
            except (httpx.HTTPError, JiraClientError) as exc:
                last_exc = exc
                if attempt >= max_attempts:
                    break
                sleep_time = backoff_base * (2 ** (attempt - 1))
                await asyncio.sleep(sleep_time)

        assert last_exc is not None
        if isinstance(last_exc, JiraClientError):
            raise last_exc
        raise JiraClientError(message="JIRA request failed", status_code=502, details=str(last_exc))

    async def _safe_response_text(self, response: httpx.Response) -> str:
        try:
            return response.text
        except Exception:
            return "<no text>"

    # PUBLIC_INTERFACE
    async def search_issues(self, jql: str, fields: Optional[List[str]] = None, max_results: int = 25) -> Dict[str, Any]:
        """
        Search issues using JQL.
        """
        params: Dict[str, Any] = {"jql": jql, "maxResults": max_results}
        if fields:
            params["fields"] = ",".join(fields)

        resp = await self._request_with_retries("GET", "/search", params=params)
        if resp.status_code >= 400:
            raise JiraClientError(
                message=f"JIRA error {resp.status_code}",
                status_code=502,
                details=await self._safe_response_text(resp),
            )
        return resp.json()

    # PUBLIC_INTERFACE
    async def create_issue(self, project_key: str, summary: str, description: Optional[str], issuetype: str) -> Dict[str, Any]:
        """
        Create a new issue in a project.
        """
        payload: Dict[str, Any] = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issuetype},
            }
        }
        if description:
            payload["fields"]["description"] = description

        resp = await self._request_with_retries("POST", "/issue", json=payload)
        if resp.status_code >= 400:
            raise JiraClientError(
                message=f"JIRA error {resp.status_code}",
                status_code=502,
                details=await self._safe_response_text(resp),
            )
        return resp.json()

    async def aclose(self) -> None:
        """Close underlying httpx client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# Dependency for FastAPI
def get_jira_client() -> JiraClient:
    """
    PUBLIC_INTERFACE
    FastAPI dependency factory for JiraClient using application settings.
    """
    settings = get_settings()
    base_url = settings.jira_base_url
    if not base_url or not settings.JIRA_EMAIL or not settings.JIRA_API_TOKEN:
        # Allow construction; errors will surface at runtime requests
        raise JiraClientError(
            message="JIRA configuration is incomplete",
            status_code=500,
            details={"base_url": base_url, "email_set": bool(settings.JIRA_EMAIL), "token_set": bool(settings.JIRA_API_TOKEN)},
        )
    return JiraClient(base_url=base_url, email=settings.JIRA_EMAIL, api_token=settings.JIRA_API_TOKEN)
