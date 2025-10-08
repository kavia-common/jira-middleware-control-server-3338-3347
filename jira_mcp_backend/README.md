# JIRA MCP Backend

A FastAPI-based Middleware Control Point (MCP) server that brokers authorized requests to Atlassian JIRA REST APIs.

## Features

- FastAPI app with root `/` and `/health` endpoints
- Security via Bearer token from environment (`AUTH_TOKEN`)
- Config via pydantic-settings: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `CORS_ALLOW_ORIGINS`, etc.
- JIRA client abstraction using `httpx` with Basic Auth
- Endpoints:
  - `GET /health` — liveness
  - `GET /ready` — readiness (checks JIRA config)
  - `GET /jira/issue/{key}` — fetch issue by key
  - `POST /jira/search` — JQL search
- Graceful 503 when JIRA configuration is missing
- CORS support
- Structured logging and consistent error responses

## Project structure

```
app/
  api/
    routes/
      health.py
      jira.py
  core/
    config.py
    security.py
  models/
    schemas.py
  services/
    jira_client.py
  main.py
```

## Requirements

See `requirements.txt`. Key libraries: FastAPI, httpx, pydantic, pydantic-settings, uvicorn.

## Environment

Copy `.env.example` to `.env` and set values (secrets omitted):

- AUTH_TOKEN
- JIRA_BASE_URL
- JIRA_EMAIL
- JIRA_API_TOKEN
- CORS_ALLOW_ORIGINS (e.g., `*` or `http://localhost:5173,https://your.app.com`)
- PORT (defaults to 3001)
- DEBUG

Do not commit real secrets.

## Run locally (example)

The preview environment typically exposes port 3001 automatically. To run locally:

```
pip install -r requirements.txt
export AUTH_TOKEN=your-token
export JIRA_BASE_URL=https://your-domain.atlassian.net
export JIRA_EMAIL=you@example.com
export JIRA_API_TOKEN=your-api-token
uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload
```

OpenAPI docs: http://localhost:3001/docs

## Authentication

Clients must include:
```
Authorization: Bearer <AUTH_TOKEN>
```

If `AUTH_TOKEN` is not configured, endpoints will return HTTP 503 with an explanatory message.

## Notes

- JIRA endpoints return 503 if credentials are missing.
- `create_issue` is implemented in the client for future use; not exposed as a route yet.
- This service does not store any secrets or tokens beyond environment variables.

## License

Apache-2.0
