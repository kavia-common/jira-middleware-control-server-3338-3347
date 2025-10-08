from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_settings
from app.core.security import get_auth_dependency
from app.models.schemas import JiraIssueResponse, JiraSearchRequest, JiraSearchResponse, ErrorResponse
from app.services.jira_client import JiraClient, JiraConfigError

router = APIRouter(prefix="/jira", tags=["JIRA"])


def get_client() -> JiraClient:
    """Dependency provider for JiraClient with current settings."""
    settings = get_settings()
    return JiraClient(
        base_url=settings.JIRA_BASE_URL,
        email=settings.JIRA_EMAIL,
        api_token=settings.JIRA_API_TOKEN,
        cloud_instance=settings.JIRA_CLOUD_INSTANCE,
    )


@router.get(
    "/issue/{key}",
    summary="Get JIRA issue by key",
    description="Fetch a JIRA issue by issue key (e.g., PROJ-123). Returns 503 if credentials not configured.",
    responses={
        200: {"model": JiraIssueResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
# PUBLIC_INTERFACE
async def get_issue(
    key: str,
    client: JiraClient = Depends(get_client),
    _: None = Depends(get_auth_dependency(get_settings())),
):
    """Fetch a JIRA issue by key using the JiraClient abstraction."""
    try:
        issue = await client.get_issue(key)
        if issue is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "not_found", "message": f"Issue '{key}' not found."},
            )
        return issue
    except JiraConfigError as cfg_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "jira_not_configured", "message": str(cfg_err)},
        )


@router.post(
    "/search",
    summary="Search JIRA issues",
    description="Search issues using JQL. Returns 503 if credentials not configured.",
    responses={
        200: {"model": JiraSearchResponse},
        401: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
# PUBLIC_INTERFACE
async def search_issues(
    payload: JiraSearchRequest,
    client: JiraClient = Depends(get_client),
    _: None = Depends(get_auth_dependency(get_settings())),
):
    """Execute a JQL search with pagination."""
    try:
        result = await client.search_issues(
            jql=payload.jql,
            start_at=payload.startAt,
            max_results=payload.maxResults,
            fields=payload.fields,
        )
        return result
    except JiraConfigError as cfg_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "jira_not_configured", "message": str(cfg_err)},
        )
