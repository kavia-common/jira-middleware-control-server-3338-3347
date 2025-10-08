import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import AppSettings, get_settings
from app.core.security import get_auth_dependency
from app.api.routes.health import router as health_router
from app.api.routes.jira import router as jira_router

# Configure root logger early
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("jira-mcp-backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup/shutdown lifecycle for resource initialization and cleanup."""
    settings = get_settings()
    # Log minimal config state (mask sensitive values)
    masked_token = (
        settings.AUTH_TOKEN[:3] + "***" if settings.AUTH_TOKEN is not None else None
    )
    logger.info(
        "Starting Jira MCP Backend | base_url=%s, email_present=%s, token=%s",
        settings.JIRA_BASE_URL,
        bool(settings.JIRA_EMAIL),
        masked_token,
    )
    yield
    logger.info("Stopping Jira MCP Backend")


def create_app(settings: Optional[AppSettings] = None) -> FastAPI:
    """Factory to create and configure FastAPI app instance."""
    settings = settings or get_settings()

    app = FastAPI(
        title="JIRA MCP Backend",
        description=(
            "Middleware Control Point server for authorized access to Atlassian JIRA APIs.\n\n"
            "This service proxies and validates requests, applying centralized auth and policy."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={"name": "MCP Server", "url": "https://example.com"},
        license_info={"name": "Apache-2.0"},
        swagger_ui_parameters={"displayRequestDuration": True},
        openapi_tags=[
            {"name": "Health", "description": "Service health and readiness endpoints."},
            {"name": "Auth", "description": "Authentication and authorization info."},
            {"name": "JIRA", "description": "JIRA proxied endpoints."},
        ],
    )

    # CORS configuration
    allow_origins = settings.CORS_ALLOW_ORIGINS or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handlers
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s %s", request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred.",
                },
            },
        )

    # Root endpoint (also protected example of dependency usage)
    @app.get(
        "/",
        tags=["Health"],
        summary="Service root",
        description="Returns a friendly service status payload.",
        response_description="Status document",
    )
    async def root(_: None = Depends(get_auth_dependency(settings))):
        return {
            "success": True,
            "service": "jira-mcp-backend",
            "version": app.version,
            "status": "ok",
        }

    # Include routers
    app.include_router(health_router)
    app.include_router(jira_router, dependencies=[Depends(get_auth_dependency(settings))])

    return app


app = create_app()
