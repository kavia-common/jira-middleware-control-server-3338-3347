# JIRA MCP Backend

A Python-based MCP (Middleware Control Point) server for JIRA, built with FastAPI. It proxies authorized requests to the JIRA REST API.

## Features
- FastAPI app with CORS, request ID middleware, and structured logging
- Simple API key authentication via `X-API-KEY` or `Authorization: Bearer`
- Health and root endpoints
- JIRA search and create issue endpoints
- Pydantic settings for configuration with `.env` support

## Getting Started

1) Create your `.env` from the example:
```
cp .env.example .env
```
Fill in:
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`
- `JIRA_BASE_URL` (or `JIRA_CLOUD_SITE`)
- `APP_API_KEYS`

2) Install Python dependencies:
```
pip install -r requirements.txt
```

3) Run the server (do not run in this task environment - for local use only):
```
uvicorn app.main:app --host 0.0.0.0 --port 3001
```

4) Explore the API docs:
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Endpoints

- `GET /` — service info
- `GET /health` — status, version, uptime
- `GET /jira/search?jql=...&fields=summary,priority&max_results=25`
- `POST /jira/issue` — body:
```json
{
  "project_key": "PROJ",
  "summary": "New task",
  "description": "Details here",
  "issuetype": "Task"
}
```

Include `X-API-KEY: <your-key>` or `Authorization: Bearer <your-key>` on secured endpoints.

## Configuration

Pydantic settings are defined in `app/core/config.py`. Required env vars for JIRA are validated at startup (warnings logged if missing). CORS can be controlled via `APP_CORS_ORIGINS`.

## Logging

Logging is configured in `app/utils/logging.py` and includes request_id, path, method, status_code, and duration in structured logs.

## Notes

- The server is expected to run on port `3001` by the preview system.
- This repo includes an example `examples/curl-examples.sh` to test endpoints quickly.
