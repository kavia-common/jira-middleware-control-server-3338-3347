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
