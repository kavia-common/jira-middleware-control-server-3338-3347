from __future__ import annotations

import asyncio
import base64
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import get_settings
from app.utils.logging import logger, timed_log_debug


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
    Async JIRA API client with basic auth and exponential backoff retries for 5xx errors,
    rate limiting (429) handling with Retry-After support, and structured debug logging.
    """

    def __init__(self, base_url: str, email: str, api_token: str, timeout: float = 15.0) -> None:
        if not base_url or not email or not api_token:
            raise ValueError("Missing JIRA configuration for client initialization.")
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

        # Cached custom field mappings with TTL
        self._field_map_cache: Optional[Tuple[float, Dict[str, str]]] = None
        self._field_map_ttl_seconds: int = 300  # 5 minutes

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Basic {self._basic_token()}",
            }
            # Use core base for default; agile endpoints will use absolute URLs
            self._client = httpx.AsyncClient(
                base_url=f"{self.base_url}/rest/api/3",
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    def _basic_token(self) -> str:
        token = base64.b64encode(f"{self.email}:{self.api_token}".encode("utf-8")).decode("utf-8")
        return token

    async def _request_with_retries(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Perform an HTTP request with retries.
        Retries on:
          - 5xx responses
          - 429 (Rate limited) honoring Retry-After header if present
          - network errors (httpx.HTTPError)
        Maps client/server errors to JiraClientError with appropriate status mapping:
          - 400, 401, 403, 404 propagate as-is
          - other 4xx -> 400
          - 5xx -> 502
        """
        settings = get_settings()
        max_attempts = max(1, int(getattr(settings, "JIRA_RETRY_MAX_ATTEMPTS", 3)))
        backoff_base = float(getattr(settings, "JIRA_RETRY_BACKOFF_BASE", 0.5))
        last_exc: Optional[Exception] = None

        # Attempt context for logging
        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            # Try to pull request_id from context by allowing caller to pass via headers if present
            request_id = None
            headers = kwargs.get("headers") or {}
            request_id = headers.get("X-Request-ID")

            with timed_log_debug(
                "jira_http_request",
                request_id=request_id,
                extra={"method": method, "url": url, "attempt": attempt},
            ):
                try:
                    client = await self._get_client()
                    resp = await client.request(method, url, **kwargs)

                    # Debug basic response info
                    logger.debug(
                        "jira_http_response",
                        extra={
                            "request_id": request_id,
                            "method": method,
                            "url": url,
                            "status_code": resp.status_code,
                            "attempt": attempt,
                        },
                    )

                    # 429 handling with Retry-After
                    if resp.status_code == 429:
                        retry_after = resp.headers.get("Retry-After")
                        try:
                            delay = float(retry_after) if retry_after is not None else backoff_base * (2 ** (attempt - 1))
                        except ValueError:
                            delay = backoff_base * (2 ** (attempt - 1))
                        if attempt < max_attempts:
                            logger.debug(
                                "jira_rate_limited_retrying",
                                extra={"request_id": request_id, "delay_s": delay, "attempt": attempt},
                            )
                            await asyncio.sleep(delay)
                            continue
                        # exceeded retries
                        raise JiraClientError(
                            message="JIRA rate limit exceeded",
                            status_code=429,
                            details=await self._safe_response_text(resp),
                        )

                    # 5xx -> retry
                    if 500 <= resp.status_code < 600:
                        if attempt < max_attempts:
                            delay = backoff_base * (2 ** (attempt - 1))
                            logger.debug(
                                "jira_server_error_retrying",
                                extra={
                                    "request_id": request_id,
                                    "status_code": resp.status_code,
                                    "delay_s": delay,
                                    "attempt": attempt,
                                },
                            )
                            await asyncio.sleep(delay)
                            continue
                        raise JiraClientError(
                            message=f"JIRA server error {resp.status_code}",
                            status_code=502,
                            details=await self._safe_response_text(resp),
                        )

                    # 4xx -> client error mapping (no retry except 429 above)
                    if 400 <= resp.status_code < 500:
                        mapped = resp.status_code if resp.status_code in (400, 401, 403, 404, 429) else 400
                        raise JiraClientError(
                            message=f"JIRA client error {resp.status_code}",
                            status_code=mapped,
                            details=await self._safe_response_text(resp),
                        )

                    return resp

                except JiraClientError as exc:
                    # Already mapped; do not retry further unless we want to for some statuses (we don't)
                    last_exc = exc
                    break
                except httpx.HTTPError as exc:
                    last_exc = exc
                    if attempt >= max_attempts:
                        break
                    delay = backoff_base * (2 ** (attempt - 1))
                    logger.debug(
                        "jira_network_error_retrying",
                        extra={"request_id": request_id, "delay_s": delay, "attempt": attempt, "error": str(exc)},
                    )
                    await asyncio.sleep(delay)

        # If we get here, retries exhausted or terminal error occurred
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
        Search issues using JQL (REST API 3).
        """
        params: Dict[str, Any] = {"jql": jql, "maxResults": max_results}
        if fields:
            params["fields"] = ",".join(fields)

        resp = await self._request_with_retries("GET", "/search", params=params)
        return resp.json()

    # PUBLIC_INTERFACE
    async def create_issue(self, project_key: str, summary: str, description: Optional[str], issuetype: str) -> Dict[str, Any]:
        """
        Create a new issue in a project (REST API 3).
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
        return resp.json()

    # Custom field mappings
    # PUBLIC_INTERFACE
    async def get_field_mappings(self) -> Dict[str, str]:
        """
        Discover and memoize custom field ids for Epic Link, Epic Name, Story points
        using the configured field display names in environment variables.

        Returns a dict like:
        {
            "story_points": "customfield_10016",
            "epic_link": "customfield_10014",
            "epic_name": "customfield_10011",
        }
        """
        # TTL check
        now = time.time()
        if self._field_map_cache and (now - self._field_map_cache[0] < self._field_map_ttl_seconds):
            return self._field_map_cache[1]

        settings = get_settings()
        sp_name = getattr(settings, "JIRA_STORY_POINTS_FIELD_NAME", None) or "Story points"
        epic_link_name = getattr(settings, "JIRA_EPIC_LINK_FIELD_NAME", None) or "Epic Link"
        epic_name_name = getattr(settings, "JIRA_EPIC_NAME_FIELD_NAME", None) or "Epic Name"

        resp = await self._request_with_retries("GET", "/field")
        fields = resp.json()

        result: Dict[str, str] = {}
        for f in fields:
            name = f.get("name")
            fid = f.get("id")
            if not name or not fid:
                continue
            lname = name.strip().lower()
            if lname == sp_name.strip().lower():
                result["story_points"] = fid
            if lname == epic_link_name.strip().lower():
                result["epic_link"] = fid
            if lname == epic_name_name.strip().lower():
                result["epic_name"] = fid

        # memoize
        self._field_map_cache = (now, result)
        return result

    # Issues and epics/stories

    # PUBLIC_INTERFACE
    async def create_epic(self, request: Any) -> Dict[str, Any]:
        """
        Create an Epic issue using the configured Epic Name custom field.
        request should have: project_key, epic_name, summary, description?
        """
        mappings = await self.get_field_mappings()
        epic_name_field = mappings.get("epic_name")
        if not epic_name_field:
            raise JiraClientError("Epic Name field mapping not found", status_code=500)

        payload = {
            "fields": {
                "project": {"key": request.project_key},
                "summary": request.summary,
                "issuetype": {"name": "Epic"},
                epic_name_field: request.epic_name,
            }
        }
        if getattr(request, "description", None):
            payload["fields"]["description"] = request.description

        resp = await self._request_with_retries("POST", "/issue", json=payload)
        return resp.json()

    # PUBLIC_INTERFACE
    async def create_story(self, request: Any) -> Dict[str, Any]:
        """
        Create a Story issue and optionally link to an epic and set story points.
        """
        payload: Dict[str, Any] = {
            "fields": {
                "project": {"key": request.project_key},
                "summary": request.summary,
                "issuetype": {"name": "Story"},
            }
        }
        if getattr(request, "description", None):
            payload["fields"]["description"] = request.description

        mappings = await self.get_field_mappings()
        # Set story points if provided
        if getattr(request, "story_points", None) is not None:
            sp_field = mappings.get("story_points")
            if not sp_field:
                raise JiraClientError("Story points field mapping not found", status_code=500)
            payload["fields"][sp_field] = request.story_points

        # Link to epic if provided (Epic Link custom field)
        if getattr(request, "parent_epic_key", None):
            epic_link_field = mappings.get("epic_link")
            if not epic_link_field:
                raise JiraClientError("Epic Link field mapping not found", status_code=500)
            payload["fields"][epic_link_field] = request.parent_epic_key

        resp = await self._request_with_retries("POST", "/issue", json=payload)
        return resp.json()

    # PUBLIC_INTERFACE
    async def link_issue_to_epic(self, epic_key_or_id: str, issue_key_or_id: str) -> Dict[str, Any]:
        """
        Link an issue to an Epic by setting the Epic Link custom field.
        """
        mappings = await self.get_field_mappings()
        epic_link_field = mappings.get("epic_link")
        if not epic_link_field:
            raise JiraClientError("Epic Link field mapping not found", status_code=500)

        payload = {"fields": {epic_link_field: epic_key_or_id}}
        await self._request_with_retries("PUT", f"/issue/{issue_key_or_id}", json=payload)
        return {"ok": True, "issue": {"key_or_id": issue_key_or_id}, "updated_field": epic_link_field}

    # PUBLIC_INTERFACE
    async def get_transitions(self, issue_key: str) -> Dict[str, Any]:
        """
        Fetch available transitions for an issue (REST API 3).
        """
        resp = await self._request_with_retries("GET", f"/issue/{issue_key}/transitions")
        return resp.json()

    # PUBLIC_INTERFACE
    async def transition_issue(self, issue_key: str, transition_id: str) -> Dict[str, Any]:
        """
        Perform a transition on an issue (REST API 3).
        """
        payload = {"transition": {"id": transition_id}}
        await self._request_with_retries("POST", f"/issue/{issue_key}/transitions", json=payload)
        # No content typically; return normalized ok payload
        return {"ok": True, "issue": issue_key, "transition_id": transition_id}

    # PUBLIC_INTERFACE
    async def add_comment(self, issue_key: str, body: str) -> Dict[str, Any]:
        """
        Add a comment to an issue (REST API 3).
        """
        payload = {"body": body}
        resp = await self._request_with_retries("POST", f"/issue/{issue_key}/comment", json=payload)
        return resp.json()

    # PUBLIC_INTERFACE
    async def estimate_story_points(self, issue_key: str, points: float) -> Dict[str, Any]:
        """
        Set story points custom field on an issue (REST API 3).
        """
        mappings = await self.get_field_mappings()
        sp_field = mappings.get("story_points")
        if not sp_field:
            raise JiraClientError("Story points field mapping not found", status_code=500)

        payload = {"fields": {sp_field: points}}
        await self._request_with_retries("PUT", f"/issue/{issue_key}", json=payload)
        return {"ok": True, "issue": issue_key, "story_points": points}

    # Agile endpoints (board, sprints, issues in sprint) use /rest/agile/1.0
    def _agile_url(self, path: str) -> str:
        return f"{self.base_url}/rest/agile/1.0{path}"

    # PUBLIC_INTERFACE
    async def list_boards(self, project_key_or_id: Optional[str] = None) -> Dict[str, Any]:
        """
        List boards, optionally filtered by projectKeyOrId (Agile 1.0).
        """
        params: Dict[str, Any] = {}
        if project_key_or_id:
            params["projectKeyOrId"] = project_key_or_id
        resp = await self._request_with_retries("GET", self._agile_url("/board"), params=params)
        return resp.json()

    # PUBLIC_INTERFACE
    async def list_sprints(self, board_id: int, state: Optional[str] = None) -> Dict[str, Any]:
        """
        List sprints for a board id (Agile 1.0).
        """
        params: Dict[str, Any] = {}
        if state:
            params["state"] = state
        resp = await self._request_with_retries("GET", self._agile_url(f"/board/{board_id}/sprint"), params=params)
        return resp.json()

    # PUBLIC_INTERFACE
    async def create_sprint(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a sprint (Agile 1.0).
        payload should include: name, originBoardId, startDate?, endDate?, goal?
        """
        resp = await self._request_with_retries("POST", self._agile_url("/sprint"), json=payload)
        return resp.json()

    # PUBLIC_INTERFACE
    async def update_sprint(self, sprint_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a sprint (Agile 1.0).
        """
        response = await self._request_with_retries("PUT", self._agile_url(f"/sprint/{sprint_id}"), json=payload)
        # Some Jira responses may have empty body; normalize to ok:true
        return response.json() if getattr(response, "text", None) else {"ok": True}

    # PUBLIC_INTERFACE
    async def move_issues_to_sprint(self, sprint_id: int, issue_keys: List[str]) -> Dict[str, Any]:
        """
        Move multiple issues to a sprint (Agile 1.0).
        """
        payload = {"issues": issue_keys}
        # Perform request and normalize possibly empty body to ok:true shape
        response = await self._request_with_retries("POST", self._agile_url(f"/sprint/{sprint_id}/issue"), json=payload)
        return response.json() if getattr(response, "text", None) else {"ok": True, "sprint_id": sprint_id, "issues": issue_keys}

    # PUBLIC_INTERFACE
    async def get_sprint_issues(self, sprint_id: int, jql_filters: Optional[str] = None) -> Dict[str, Any]:
        """
        Get issues for a sprint (Agile 1.0). Optionally filter using JQL via 'jql' param.
        """
        params: Dict[str, Any] = {}
        if jql_filters:
            params["jql"] = jql_filters
        resp = await self._request_with_retries("GET", self._agile_url(f"/sprint/{sprint_id}/issue"), params=params)
        return resp.json()

    # PUBLIC_INTERFACE
    async def search_issues_via_params(
        self,
        project: Optional[str] = None,
        board_id: Optional[int] = None,
        sprint_id: Optional[int] = None,
        assignee: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convenience JQL search builder from params.
        """
        clauses: List[str] = []
        if project:
            clauses.append(f'project = "{project}"')
        if assignee:
            clauses.append(f'assignee = "{assignee}"')
        if status:
            clauses.append(f'status = "{status}"')
        # sprint/board handling: sprint id directly if provided
        if sprint_id is not None:
            clauses.append(f"sprint = {sprint_id}")
        # board filter generally through sprint; if provided without sprint, return empty unless otherwise desired
        jql = " AND ".join(clauses) if clauses else ""
        return await self.search_issues(jql=jql or "order by created DESC", fields=None, max_results=50)

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
        raise JiraClientError(
            message="JIRA configuration is incomplete",
            status_code=500,
            details={
                "base_url": base_url,
                "email_set": bool(settings.JIRA_EMAIL),
                "token_set": bool(settings.JIRA_API_TOKEN),
            },
        )
    return JiraClient(base_url=base_url, email=settings.JIRA_EMAIL, api_token=settings.JIRA_API_TOKEN)
