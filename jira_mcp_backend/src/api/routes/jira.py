from __future__ import annotations

from fastapi import APIRouter, Depends, Path, status

from ...clients.jira_client import JiraClient
from ...core.security import AuthenticatedClient, get_current_client
from ...models.common import GenericResponse, SearchQuery
from ...models.jira import (
    AddCommentRequest,
    CreateIssueRequest,
    CreateIssueResponse,
    JiraIssue,
    TransitionIssueRequest,
)

router = APIRouter(prefix="/jira", tags=["JIRA"])


@router.get(
    "/issues/{issue_key}",
    summary="Get Issue",
    response_model=JiraIssue,
    responses={404: {"description": "Issue not found"}},
)
async def get_issue(
    issue_key: str = Path(..., description="JIRA issue key"),
    auth: AuthenticatedClient = Depends(get_current_client),
    jira: JiraClient = Depends(),
):
    """Retrieve a JIRA issue by key."""
    data = await jira.get_issue(issue_key)
    return JiraIssue(id=data.get("id"), key=data.get("key"), fields=data.get("fields", {}))


@router.post(
    "/issues",
    summary="Create Issue",
    response_model=CreateIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_issue(
    payload: CreateIssueRequest,
    auth: AuthenticatedClient = Depends(get_current_client),
    jira: JiraClient = Depends(),
):
    """Create a new JIRA issue."""
    p = payload.fields
    data = await jira.create_issue(project_key=p.project_key, summary=p.summary, issuetype_name=p.issuetype_name, description=p.description)
    return CreateIssueResponse(id=data.get("id", ""), key=data.get("key", ""), self=data.get("self"))


@router.post(
    "/issues/{issue_key}/transitions",
    summary="Transition Issue",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def transition_issue(
    issue_key: str,
    payload: TransitionIssueRequest,
    auth: AuthenticatedClient = Depends(get_current_client),
    jira: JiraClient = Depends(),
):
    """Transition an issue to a new status using transition ID."""
    await jira.transition_issue(issue_key, payload.transition_id)
    return None


@router.post(
    "/issues/{issue_key}/comments",
    summary="Add Comment",
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    issue_key: str,
    payload: AddCommentRequest,
    auth: AuthenticatedClient = Depends(get_current_client),
    jira: JiraClient = Depends(),
):
    """Add a comment to the specified issue."""
    data = await jira.add_comment(issue_key, payload.body)
    return GenericResponse(data=data)


@router.post(
    "/search",
    summary="Search Issues",
    response_model=GenericResponse,
)
async def search_issues(
    query: SearchQuery,
    auth: AuthenticatedClient = Depends(get_current_client),
    jira: JiraClient = Depends(),
):
    """Search JIRA issues with JQL."""
    data = await jira.search(jql=query.jql, start_at=query.start_at, max_results=query.max_results, fields=query.fields)
    return GenericResponse(data=data)
