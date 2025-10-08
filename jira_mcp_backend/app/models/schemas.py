from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error model for consistent JSON responses."""
    code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human-readable error message")


class JiraIssueResponse(BaseModel):
    """Minimal issue response passthrough schema (loosely typed)."""
    id: Optional[str] = Field(default=None, description="Issue id")
    key: Optional[str] = Field(default=None, description="Issue key")
    fields: Optional[Dict[str, Any]] = Field(default=None, description="Issue fields bag")

    class Config:
        extra = "allow"


# PUBLIC_INTERFACE
class JiraSearchRequest(BaseModel):
    """Request body for JQL search."""
    jql: str = Field(..., description="JQL query string")
    startAt: int = Field(0, description="Starting index for pagination")
    maxResults: int = Field(50, description="Maximum results to return")
    fields: Optional[List[str]] = Field(default=None, description="Optional list of fields to include")


# PUBLIC_INTERFACE
class JiraSearchResponse(BaseModel):
    """Response body for JQL search (loosely typed passthrough)."""
    startAt: int = Field(..., description="Start index")
    maxResults: int = Field(..., description="Max results requested")
    total: int = Field(..., description="Total results available")
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="List of issues")

    class Config:
        extra = "allow"
