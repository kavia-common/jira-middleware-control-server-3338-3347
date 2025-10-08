from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, status

from app.models.jira import (
    CapacityRequest,
    CapacityResponse,
    CreateEpicRequest,
    CreateIssueRequest,
    CreateSprintRequest,
    CreateStoryRequest,
    JiraSearchResponse,
    LinkIssueToEpicRequest,
    MoveIssuesToSprintRequest,
    UpdateSprintRequest,
)
from app.services.jira_client import JiraClient, JiraClientError, get_jira_client

api_router = APIRouter()


def _wrap_success(data: Any, request: Request) -> Dict[str, Any]:
    """Wrap success responses to include data and request_id."""
    return {
        "data": data,
        "request_id": getattr(request.state, "request_id", None),
    }


def _raise_http_error(e: JiraClientError, request: Request) -> None:
    """Map JiraClientError to HTTPException with standardized body and request correlation."""
    code = "jira_error"
    message = e.message
    details = e.details
    status_code = getattr(e, "status_code", 502) or 502
    raise HTTPException(
        status_code=status_code,
        detail={
            "error": {"code": code, "message": message, "details": details},
            "request_id": getattr(request.state, "request_id", None),
        },
    )


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
        404: {"description": "Not Found"},
        429: {"description": "Rate Limited"},
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
        _raise_http_error(e, request)  # type: ignore[return-value]


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
    x_idempotency_key: Optional[str] = Header(default=None, convert_underscores=False, alias="X-Idempotency-Key"),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Create a JIRA issue in a project with summary, description, and type.
    """
    try:
        # Idempotency delegation where supported by client or JIRA
        created = await client.create_issue(
            project_key=payload.project_key,
            summary=payload.summary,
            description=payload.description,
            issuetype=payload.issuetype,
        )
        return {"issue": created, "request_id": getattr(request.state, "request_id", None)}
    except JiraClientError as e:
        _raise_http_error(e, request)  # type: ignore[return-value]


# Sprint ceremonies and related endpoints


@api_router.post(
    "/jira/epic",
    tags=["jira"],
    summary="Create an Epic",
    responses={201: {"description": "Created"}, 400: {"description": "Bad Request"}, 401: {"description": "Unauthorized"}, 502: {"description": "Bad Gateway"}},
    status_code=status.HTTP_201_CREATED,
)
async def create_epic(
    request: Request,
    payload: CreateEpicRequest,
    client: JiraClient = Depends(get_jira_client),
    x_idempotency_key: Optional[str] = Header(default=None, convert_underscores=False, alias="X-Idempotency-Key"),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Create an Epic with Epic Name custom field.
    """
    try:
        epic = await client.create_epic(payload)
        return _wrap_success({"issue": epic}, request)
    except JiraClientError as e:
        _raise_http_error(e, request)  # type: ignore[return-value]


@api_router.post(
    "/jira/story",
    tags=["jira"],
    summary="Create a Story",
    responses={201: {"description": "Created"}, 400: {"description": "Bad Request"}, 401: {"description": "Unauthorized"}, 502: {"description": "Bad Gateway"}},
    status_code=status.HTTP_201_CREATED,
)
async def create_story(
    request: Request,
    payload: CreateStoryRequest,
    client: JiraClient = Depends(get_jira_client),
    x_idempotency_key: Optional[str] = Header(default=None, convert_underscores=False, alias="X-Idempotency-Key"),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Create a Story, optionally setting story points and linking to an epic.
    """
    try:
        story = await client.create_story(payload)
        return _wrap_success({"issue": story}, request)
    except JiraClientError as e:
        _raise_http_error(e, request)  # type: ignore[return-value]


@api_router.post(
    "/jira/epic/link",
    tags=["jira"],
    summary="Link an issue to an Epic",
    responses={200: {"description": "OK"}, 400: {"description": "Bad Request"}, 401: {"description": "Unauthorized"}, 404: {"description": "Not Found"}, 502: {"description": "Bad Gateway"}},
)
async def link_issue_to_epic(
    request: Request,
    payload: LinkIssueToEpicRequest,
    client: JiraClient = Depends(get_jira_client),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Link an issue to an Epic by setting the Epic Link custom field.
    """
    try:
        res = await client.link_issue_to_epic(epic_key_or_id=payload.epic_key_or_id, issue_key_or_id=payload.issue_key_or_id)
        return _wrap_success(res, request)
    except JiraClientError as e:
        _raise_http_error(e, request)  # type: ignore[return-value]


@api_router.get(
    "/jira/boards",
    tags=["jira"],
    summary="List boards",
    responses={200: {"description": "OK"}, 400: {"description": "Bad Request"}, 401: {"description": "Unauthorized"}, 502: {"description": "Bad Gateway"}},
)
async def list_boards(
    request: Request,
    project_key_or_id: Optional[str] = Query(default=None, description="Filter by project key or id"),
    client: JiraClient = Depends(get_jira_client),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    List JIRA boards (Agile).
    """
    try:
        boards = await client.list_boards(project_key_or_id=project_key_or_id)
        return _wrap_success(boards, request)
    except JiraClientError as e:
        _raise_http_error(e, request)  # type: ignore[return-value]


@api_router.get(
    "/jira/boards/{boardId}/sprints",
    tags=["jira"],
    summary="List sprints for board",
    responses={200: {"description": "OK"}, 400: {"description": "Bad Request"}, 401: {"description": "Unauthorized"}, 502: {"description": "Bad Gateway"}},
)
async def list_sprints(
    request: Request,
    boardId: int = Path(..., description="Board ID"),
    state: Optional[str] = Query(default=None, description='Filter by state: "future,active,closed"'),
    client: JiraClient = Depends(get_jira_client),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    List sprints for a given board.
    """
    # Validate state filter if provided
    if state and state not in {"future", "active", "closed"}:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "invalid_state", "message": "Invalid state filter", "details": {"allowed": ["future", "active", "closed"]}}, "request_id": getattr(request.state, "request_id", None)},
        )
    try:
        sprints = await client.list_sprints(board_id=boardId, state=state)
        return _wrap_success(sprints, request)
    except JiraClientError as e:
        _raise_http_error(e, request)  # type: ignore[return-value]


@api_router.post(
    "/jira/sprints",
    tags=["jira"],
    summary="Create sprint",
    responses={201: {"description": "Created"}, 400: {"description": "Bad Request"}, 401: {"description": "Unauthorized"}, 502: {"description": "Bad Gateway"}},
    status_code=status.HTTP_201_CREATED,
)
async def create_sprint(
    request: Request,
    payload: CreateSprintRequest,
    client: JiraClient = Depends(get_jira_client),
    x_idempotency_key: Optional[str] = Header(default=None, convert_underscores=False, alias="X-Idempotency-Key"),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Create a sprint on a board.
    """
    try:
        json_payload: Dict[str, Any] = {
            "name": payload.name,
            "originBoardId": payload.board_id,
        }
        if payload.start_date:
            json_payload["startDate"] = payload.start_date
        if payload.end_date:
            json_payload["endDate"] = payload.end_date
        if payload.goal:
            json_payload["goal"] = payload.goal
        sprint = await client.create_sprint(json_payload)
        return _wrap_success(sprint, request)
    except JiraClientError as e:
        _raise_http_error(e, request)  # type: ignore[return-value]


@api_router.put(
    "/jira/sprints/{sprintId}",
    tags=["jira"],
    summary="Update sprint",
    responses={200: {"description": "OK"}, 400: {"description": "Bad Request"}, 401: {"description": "Unauthorized"}, 404: {"description": "Not Found"}, 502: {"description": "Bad Gateway"}},
)
async def update_sprint(
    request: Request,
    sprintId: int = Path(..., description="Sprint ID"),
    payload: UpdateSprintRequest = ...,
    client: JiraClient = Depends(get_jira_client),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Update a sprint.
    """
    try:
        json_payload: Dict[str, Any] = {}
        if payload.name is not None:
            json_payload["name"] = payload.name
        if payload.start_date is not None:
            json_payload["startDate"] = payload.start_date
        if payload.end_date is not None:
            json_payload["endDate"] = payload.end_date
        if payload.goal is not None:
            json_payload["goal"] = payload.goal
        res = await client.update_sprint(sprint_id=sprintId, payload=json_payload)
        return _wrap_success(res, request)
    except JiraClientError as e:
        _raise_http_error(e, request)  # type: ignore[return-value]


@api_router.post(
    "/jira/sprints/{sprintId}/issues",
    tags=["jira"],
    summary="Move issues to sprint",
    responses={200: {"description": "OK"}, 400: {"description": "Bad Request"}, 401: {"description": "Unauthorized"}, 404: {"description": "Not Found"}, 502: {"description": "Bad Gateway"}},
)
async def move_issues_to_sprint(
    request: Request,
    sprintId: int = Path(..., description="Sprint ID"),
    payload: MoveIssuesToSprintRequest = ...,
    client: JiraClient = Depends(get_jira_client),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Move a batch of issues (max 100) to a sprint.
    """
    if len(payload.issue_keys) == 0:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "empty_batch", "message": "issue_keys must not be empty", "details": None}, "request_id": getattr(request.state, "request_id", None)},
        )
    if len(payload.issue_keys) > 100:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "batch_too_large", "message": "Max 100 issues per request", "details": {"limit": 100}}, "request_id": getattr(request.state, "request_id", None)},
        )
    try:
        res = await client.move_issues_to_sprint(sprint_id=sprintId, issue_keys=payload.issue_keys)
        return _wrap_success(res, request)
    except JiraClientError as e:
        _raise_http_error(e, request)  # type: ignore[return-value]


@api_router.get(
    "/jira/sprints/{sprintId}/issues",
    tags=["jira"],
    summary="Get sprint issues",
    responses={200: {"description": "OK"}, 400: {"description": "Bad Request"}, 401: {"description": "Unauthorized"}, 404: {"description": "Not Found"}, 502: {"description": "Bad Gateway"}},
)
async def get_sprint_issues(
    request: Request,
    sprintId: int = Path(..., description="Sprint ID"),
    jql_filters: Optional[str] = Query(default=None, description="Optional additional JQL clauses"),
    client: JiraClient = Depends(get_jira_client),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Fetch issues in a sprint with optional JQL filtering.
    """
    try:
        issues = await client.get_sprint_issues(sprint_id=sprintId, jql_filters=jql_filters)
        return _wrap_success(issues, request)
    except JiraClientError as e:
        _raise_http_error(e, request)  # type: ignore[return-value]


@api_router.get(
    "/jira/issues",
    tags=["jira"],
    summary="Filtered issues search via params",
    responses={200: {"description": "OK"}, 400: {"description": "Bad Request"}, 401: {"description": "Unauthorized"}, 502: {"description": "Bad Gateway"}},
)
async def issues_via_params(
    request: Request,
    project: Optional[str] = Query(default=None, description="Project key"),
    board_id: Optional[int] = Query(default=None, description="Board ID (info only; use sprintId to filter)"),
    sprint_id: Optional[int] = Query(default=None, description="Sprint ID"),
    assignee: Optional[str] = Query(default=None, description="Assignee display name or accountId"),
    status: Optional[str] = Query(default=None, description="Workflow status name"),
    client: JiraClient = Depends(get_jira_client),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Search issues using simple filters; builds JQL internally.
    """
    try:
        result = await client.search_issues_via_params(
            project=project, board_id=board_id, sprint_id=sprint_id, assignee=assignee, status=status
        )
        return _wrap_success(result, request)
    except JiraClientError as e:
        _raise_http_error(e, request)  # type: ignore[return-value]


@api_router.post(
    "/jira/issues/{issueKey}/transition",
    tags=["jira"],
    summary="Transition issue",
    responses={200: {"description": "OK"}, 400: {"description": "Bad Request"}, 401: {"description": "Unauthorized"}, 404: {"description": "Not Found"}, 502: {"description": "Bad Gateway"}},
)
async def transition_issue(
    request: Request,
    issueKey: str = Path(..., description="Issue key"),
    transition_id: Optional[str] = Query(default=None, description="Transition ID"),
    transition_name: Optional[str] = Query(default=None, description="Transition name (resolved to ID if provided)"),
    client: JiraClient = Depends(get_jira_client),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Transition an issue by ID or by resolving a transition name to ID.
    """
    try:
        resolved_transition_id = transition_id
        if not resolved_transition_id and transition_name:
            transitions = await client.get_transitions(issueKey)
            ids = [t.get("id") for t in transitions.get("transitions", []) if t.get("name") == transition_name]
            if not ids:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": {"code": "invalid_transition", "message": "Transition name not available for issue", "details": {"name": transition_name}},
                        "request_id": getattr(request.state, "request_id", None),
                    },
                )
            resolved_transition_id = ids[0]
        if not resolved_transition_id:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "missing_transition", "message": "Provide transition_id or transition_name", "details": None}, "request_id": getattr(request.state, "request_id", None)},
            )
        res = await client.transition_issue(issue_key=issueKey, transition_id=resolved_transition_id)
        return _wrap_success(res, request)
    except JiraClientError as e:
        _raise_http_error(e, request)  # type: ignore[return-value]


@api_router.post(
    "/jira/issues/{issueKey}/comments",
    tags=["jira"],
    summary="Add comment to issue",
    responses={201: {"description": "Created"}, 400: {"description": "Bad Request"}, 401: {"description": "Unauthorized"}, 404: {"description": "Not Found"}, 502: {"description": "Bad Gateway"}},
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    request: Request,
    issueKey: str = Path(..., description="Issue key"),
    body: str = Query(..., description="Comment body"),
    client: JiraClient = Depends(get_jira_client),
    x_idempotency_key: Optional[str] = Header(default=None, convert_underscores=False, alias="X-Idempotency-Key"),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Add a comment to an issue.
    """
    try:
        res = await client.add_comment(issue_key=issueKey, body=body)
        return _wrap_success(res, request)
    except JiraClientError as e:
        _raise_http_error(e, request)  # type: ignore[return-value]


@api_router.put(
    "/jira/issues/{issueKey}/estimate",
    tags=["jira"],
    summary="Set story points estimate",
    responses={200: {"description": "OK"}, 400: {"description": "Bad Request"}, 401: {"description": "Unauthorized"}, 404: {"description": "Not Found"}, 502: {"description": "Bad Gateway"}},
)
async def set_estimate(
    request: Request,
    issueKey: str = Path(..., description="Issue key"),
    points: float = Query(..., ge=0, description="Story points value"),
    client: JiraClient = Depends(get_jira_client),
) -> Dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Set the story points on an issue via custom field mapping.
    """
    try:
        res = await client.estimate_story_points(issue_key=issueKey, points=points)
        return _wrap_success(res, request)
    except JiraClientError as e:
        _raise_http_error(e, request)  # type: ignore[return-value]


# Capacity planning


@api_router.post(
    "/capacity/plan",
    tags=["jira"],
    summary="Compute sprint capacity",
    response_model=CapacityResponse,
    responses={200: {"description": "OK"}, 400: {"description": "Bad Request"}},
)
async def capacity_plan(
    request: Request,
    payload: CapacityRequest,
) -> CapacityResponse:
    """
    PUBLIC_INTERFACE
    Compute a simple capacity plan for a team given sprint days and hours/day.
    """
    if payload.sprint_days <= 0 or payload.hours_per_day <= 0:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "invalid_capacity_args", "message": "sprint_days and hours_per_day must be positive", "details": None}, "request_id": getattr(request.state, "request_id", None)},
        )
    member_count = len(payload.team_members)
    total_member_days = member_count * payload.sprint_days
    total_hours = float(total_member_days) * float(payload.hours_per_day)
    return CapacityResponse(total_member_days=total_member_days, total_hours=total_hours, request_id=getattr(request.state, "request_id", None))
