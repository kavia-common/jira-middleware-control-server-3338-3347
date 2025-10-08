from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class IssueFields(BaseModel):
    project_key: str = Field(..., description="Project key (e.g., PROJ)")
    summary: str = Field(..., description="Issue summary/title")
    description: Optional[str] = Field(default=None, description="Issue description")
    issuetype_name: str = Field(..., description="Issue type name (e.g., Task, Bug)")


class CreateIssueRequest(BaseModel):
    fields: IssueFields = Field(..., description="Issue fields")


class CreateIssueResponse(BaseModel):
    id: str = Field(..., description="Created issue ID")
    key: str = Field(..., description="Created issue key")
    self: Optional[str] = Field(default=None, description="Self URL")


class TransitionIssueRequest(BaseModel):
    transition_id: str = Field(..., description="Transition ID to move issue to")


class AddCommentRequest(BaseModel):
    body: str = Field(..., description="Comment text body")


class JiraIssue(BaseModel):
    id: str = Field(..., description="Issue ID")
    key: str = Field(..., description="Issue key")
    fields: Dict[str, Any] = Field(default_factory=dict, description="Issue fields payload")


class SearchIssuesResponse(BaseModel):
    startAt: int = Field(..., description="Start offset")
    maxResults: int = Field(..., description="Max results")
    total: int = Field(..., description="Total results")
    issues: list[JiraIssue] = Field(default_factory=list, description="Issues result list")
