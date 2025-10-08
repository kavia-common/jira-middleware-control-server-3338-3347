from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(prefix="", tags=["Health"])


@router.get(
    "/health",
    summary="Health check",
    description="Returns service liveness status.",
)
# PUBLIC_INTERFACE
def health():
    """Basic liveness endpoint."""
    return {"success": True, "status": "healthy"}


@router.get(
    "/ready",
    summary="Readiness check",
    description="Checks minimal configuration readiness for JIRA connectivity.",
)
# PUBLIC_INTERFACE
def ready():
    """Readiness endpoint indicating if minimal JIRA configuration exists."""
    settings = get_settings()
    ready_state = bool(settings.JIRA_BASE_URL and settings.JIRA_EMAIL and settings.JIRA_API_TOKEN)
    return {
        "success": ready_state,
        "status": "ready" if ready_state else "not_ready",
        "jiraConfigured": ready_state,
    }
