from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import get_settings
from ..core.errors import install_exception_handlers
from ..core.logging import configure_logging, install_request_logging
from .routes.jira import router as jira_router

settings = get_settings()
configure_logging(settings.LOG_LEVEL)

app = FastAPI(
    title=settings.APP_NAME,
    description="FastAPI-based JIRA MCP Server",
    version="1.0.0",
    openapi_tags=[
        {"name": "JIRA", "description": "Endpoints to interact with JIRA"},
        {"name": "Health", "description": "Health and diagnostics"},
    ],
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging
install_request_logging(app)
# Exceptions
install_exception_handlers(app)


# PUBLIC_INTERFACE
@app.get("/", tags=["Health"], summary="Health Check")
def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "app": settings.APP_NAME, "environment": settings.APP_ENV}


# Mount versioned API
from fastapi import APIRouter  # noqa: E402

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(jira_router)
app.include_router(api_v1)
