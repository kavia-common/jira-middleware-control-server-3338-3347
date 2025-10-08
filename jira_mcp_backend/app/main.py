from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.api.routes import api_router
from app.core.config import Settings, get_settings
from app.utils.logging import configure_logging, logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that attaches a unique request_id to each incoming request
    and includes it in response headers and structured logs.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req-{int(time.time() * 1000)}"
        start = time.perf_counter()

        # attach to state for downstream usage
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.exception(
                "unhandled_exception",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = request_id

        # best-effort to get status
        status_code = getattr(response, "status_code", 0)
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


def read_version() -> str:
    """Read version from VERSION file with fallback."""
    try:
        version_path = Path(__file__).resolve().parent.parent / "VERSION"
        return version_path.read_text(encoding="utf-8").strip() or "0.1.0"
    except Exception:
        return "0.1.0"


def build_app() -> FastAPI:
    """
    PUBLIC_INTERFACE
    Create and configure the FastAPI application, including routes, middleware, and exception handlers.
    """
    settings: Settings = get_settings()

    # Configure logging early
    configure_logging(level=settings.LOG_LEVEL)

    app = FastAPI(
        title="JIRA MCP Backend",
        description="Middleware Control Point server to proxy authorized requests to JIRA APIs.",
        version=read_version(),
        contact={"name": "MCP Backend", "url": "https://example.com"},
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "root", "description": "Service information and health"},
            {"name": "jira", "description": "JIRA-proxy endpoints"},
        ],
    )

    # CORS
    allow_origins = settings.APP_CORS_ORIGINS or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    app.add_middleware(RequestIDMiddleware)

    # Auth middleware (added via app.middleware stack to access path)
    from app.middleware.auth import api_key_auth_middleware
    app.middleware("http")(api_key_auth_middleware)

    # Include API router
    app.include_router(api_router)

    # Root endpoint
    @app.get("/", tags=["root"], summary="Service info", include_in_schema=True)
    async def root(request: Request) -> Dict[str, Any]:
        """
        PUBLIC_INTERFACE
        Returns basic service information including name, description and docs URL.
        """
        return {
            "name": "JIRA MCP Backend",
            "description": "A middleware service that proxies authorized client requests to JIRA.",
            "docs_url": str(request.base_url) + "docs",
            "request_id": getattr(request.state, "request_id", None),
        }

    # Health endpoint at app-level for redundancy
    start_time = time.time()

    @app.get("/health", tags=["root"], summary="Health check")
    async def health(request: Request) -> Dict[str, Any]:
        """
        PUBLIC_INTERFACE
        Returns health information including status, version, and uptime.
        """
        uptime_seconds = int(time.time() - start_time)
        return {
            "status": "ok",
            "version": read_version(),
            "uptime_seconds": uptime_seconds,
            "request_id": getattr(request.state, "request_id", None),
        }

    # Global exception handlers
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            "unhandled_exception",
            extra={"request_id": request_id, "path": request.url.path, "method": request.method},
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred.",
                    "details": str(exc),
                },
                "request_id": request_id,
            },
        )

    # Startup validation for required env vars
    @app.on_event("startup")
    async def validate_config_on_startup():
        missing: list[str] = []
        if not settings.JIRA_EMAIL:
            missing.append("JIRA_EMAIL")
        if not settings.JIRA_API_TOKEN:
            missing.append("JIRA_API_TOKEN")
        if not (settings.JIRA_BASE_URL or settings.JIRA_CLOUD_SITE):
            missing.append("JIRA_BASE_URL or JIRA_CLOUD_SITE")
        if missing:
            logger.warning(
                "missing_env_variables",
                extra={"missing": missing},
            )

    # Graceful shutdown hook placeholder
    @app.on_event("shutdown")
    async def shutdown_event():
        # Allow pending tasks to finish briefly
        await asyncio.sleep(0)

    return app


app = build_app()

# For uvicorn: uvicorn app.main:app --host 0.0.0.0 --port 3001
