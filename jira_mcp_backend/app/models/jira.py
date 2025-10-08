from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class JiraSearchResult(BaseModel):
    """Represents a simplified view of a JIRA search result if needed."""
    total: int = Field(default=0, description="Total number of issues matching")
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="Raw issues list")


class JiraSearchResponse(JiraSearchResult):
    """Extends search result with request id."""
    request_id: Optional[str] = Field(default=None, description="Per-request identifier")


class CreateIssueRequest(BaseModel):
    """
    PUBLIC_INTERFACE
    Request model for creating a JIRA issue.
    """
    project_key: str = Field(..., description="Project key, e.g., PROJ")
    summary: str = Field(..., description="Short summary/title of the issue")
    description: Optional[str] = Field(default=None, description="Detailed description")
    issuetype: str = Field(..., description='Issue type name, e.g., "Task", "Bug"')


# Sprint ceremonies and related models

# PUBLIC_INTERFACE
class CreateEpicRequest(BaseModel):
    """Request for creating an Epic issue."""
    project_key: str = Field(..., description="Project key for the Epic")
    epic_name: str = Field(..., description="Epic Name (custom field)")
    summary: str = Field(..., description="Summary/title for the Epic")
    description: Optional[str] = Field(default=None, description="Epic description")


# PUBLIC_INTERFACE
class CreateStoryRequest(BaseModel):
    """Request for creating a Story issue."""
    project_key: str = Field(..., description="Project key for the Story")
    summary: str = Field(..., description="Summary/title for the Story")
    description: Optional[str] = Field(default=None, description="Story description")
    parent_epic_key: Optional[str] = Field(default=None, description="Epic key to link this Story to")
    story_points: Optional[float] = Field(default=None, description="Estimate in Story Points")


# PUBLIC_INTERFACE
class LinkIssueToEpicRequest(BaseModel):
    """Request to link an issue to an epic."""
    epic_key_or_id: str = Field(..., description="Epic key (e.g., PROJ-1) or numeric ID")
    issue_key_or_id: str = Field(..., description="Issue key or numeric ID to link")


# PUBLIC_INTERFACE
class TransitionIssueRequest(BaseModel):
    """Request to transition an issue via workflow."""
    issue_key: str = Field(..., description="Issue key to transition")
    transition_id: str = Field(..., description="Transition ID to apply")


# PUBLIC_INTERFACE
class AddCommentRequest(BaseModel):
    """Request to add a comment to an issue."""
    issue_key: str = Field(..., description="Issue key to comment on")
    body: str = Field(..., description="Comment body (can be simple text/ADF)")


# PUBLIC_INTERFACE
class EstimateStoryPointsRequest(BaseModel):
    """Request to set the Story Points estimate on an issue."""
    issue_key: str = Field(..., description="Issue key to estimate")
    points: float = Field(..., description="Story Points value")


# PUBLIC_INTERFACE
class CreateSprintRequest(BaseModel):
    """Request for creating a sprint."""
    name: str = Field(..., description="Sprint name")
    board_id: int = Field(..., description="Board ID the sprint belongs to")
    start_date: Optional[str] = Field(default=None, description="ISO8601 start date")
    end_date: Optional[str] = Field(default=None, description="ISO8601 end date")
    goal: Optional[str] = Field(default=None, description="Sprint goal text")


# PUBLIC_INTERFACE
class UpdateSprintRequest(BaseModel):
    """Request for updating a sprint."""
    name: Optional[str] = Field(default=None, description="New sprint name")
    start_date: Optional[str] = Field(default=None, description="ISO8601 start date")
    end_date: Optional[str] = Field(default=None, description="ISO8601 end date")
    goal: Optional[str] = Field(default=None, description="Sprint goal")


# PUBLIC_INTERFACE
class MoveIssuesToSprintRequest(BaseModel):
    """Request for moving issues to a sprint."""
    sprint_id: int = Field(..., description="Target sprint ID")
    issue_keys: List[str] = Field(..., description="Issue keys to move")


# Minimal response envelopes to keep routes consistent

# PUBLIC_INTERFACE
class SimpleIssueResponse(BaseModel):
    """Minimal wrapper for an issue operation response."""
    issue: Dict[str, Any] = Field(..., description="Raw issue object from JIRA")
    request_id: Optional[str] = Field(default=None, description="Per-request identifier")


# PUBLIC_INTERFACE
class SimpleOKResponse(BaseModel):
    """Generic ok response with optional payload."""
    ok: bool = Field(default=True, description="Indicates success")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Optional response data")
    request_id: Optional[str] = Field(default=None, description="Per-request identifier")


# PUBLIC_INTERFACE
class CapacityRequest(BaseModel):
    """Represents a team's capacity request for planning purposes."""
    team_members: List[str] = Field(..., description="Usernames or accountIds of team members")
    sprint_days: int = Field(..., description="Number of working days in the sprint")
    hours_per_day: float = Field(..., description="Hours per day per member")


# PUBLIC_INTERFACE
class CapacityResponse(BaseModel):
    """Computed capacity response."""
    total_member_days: int = Field(..., description="Total member-days")
    total_hours: float = Field(..., description="Total capacity hours")
    request_id: Optional[str] = Field(default=None, description="Per-request identifier")
