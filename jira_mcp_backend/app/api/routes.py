from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.models.jira import CreateIssueRequest, JiraSearchResponse
from app.services.jira_client import JiraClient, JiraClientError, get_jira_client

api_router = APIRouter()


@api_router.get(
    "/health",
    tags=["root"],
    summary="Health check",
    response_model=Dict[str, Any],
)
async def health(request: Request) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Health check endpoint returning status, version, and uptime. Duplicated at app level for convenience.
    """
    from app.main import read_version  # lazy import to avoid cycles
    return {
        "status": "ok",
        "version": read_version(),
        "request_id": getattr(request.state, "request_id", None),
    }


@api_router.get(
    "/jira/search",
    tags=["jira"],
    summary="Search JIRA issues",
    response_model=JiraSearchResponse,
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        502: {"description": "Bad Gateway"},
    },
)
async def jira_search(
    request: Request,
    jql: str = Query(..., description="JQL query string"),
    fields: Optional[List[str]] = Query(None, description="Fields to include"),
    max_results: int = Query(25, ge=1, le=100, description="Max results"),
    client: JiraClient = Depends(get_jira_client),
) -> JiraSearchResponse:
    """
    PUBLIC_INTERFACE
    Proxy to JIRA search API with JQL and optional fields/max_results.
    """
    try:
        result = await client.search_issues(jql=jql, fields=fields, max_results=max_results)
        return JiraSearchResponse(
            total=result.get("total", 0),
            issues=result.get("issues", []),
            request_id=getattr(request.state, "request_id", None),
        )
    except JiraClientError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"code": "jira_error", "message": e.message, "details": e.details},
        )


@api_router.post(
    "/jira/issue",
    tags=["jira"],
    summary="Create JIRA issue",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        502: {"description": "Bad Gateway"},
    },
)
async def jira_create_issue(
    request: Request,
    payload: CreateIssueRequest,
    client: JiraClient = Depends(get_jira_client),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Create a JIRA issue in a project with summary, description, and type.
    """
    try:
        created = await client.create_issue(
            project_key=payload.project_key,
            summary=payload.summary,
            description=payload.description,
            issuetype=payload.issuetype,
        )
        return {"issue": created, "request_id": getattr(request.state, "request_id", None)}
    except JiraClientError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"code": "jira_error", "message": e.message, "details": e.details},
        )
