from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Simple health check response."""
    status: str = Field(..., description="Service status")
    app: str = Field(..., description="Application name")
    environment: str = Field(..., description="Application environment")


class SearchQuery(BaseModel):
    """Generic search query payload."""
    jql: str = Field(..., description="JQL string for JIRA search")
    start_at: int = Field(default=0, ge=0, description="Offset for search results")
    max_results: int = Field(default=50, ge=1, le=100, description="Maximum results to return")
    fields: Optional[list[str]] = Field(default=None, description="Fields to include in results")


class GenericResponse(BaseModel):
    """Generic pass-through JSON response for upstream data."""
    data: Dict[str, Any] = Field(default_factory=dict, description="Wrapped upstream response data")
