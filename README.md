# JIRA MCP Server

A Python-based MCP (Middleware Control Point) server for JIRA using FastAPI. It provides a secure, consistent interface for authorized clients to interact with JIRA.

## Features
- FastAPI app with versioned routes under `/api/v1/jira`
- API key authentication (primary). JWT optional stub not implemented by default.
- Async JIRA client using httpx
- Structured logging and centralized error handling
- OpenAPI generation script to `interfaces/openapi.json`
- Tests for health, auth, and JIRA routes (mocked)

## Quick Start

1) Create and configure environment
- Copy `.env.example` to `.env` and set values

2) Install dependencies
```
pip install -r jira_mcp_backend/requirements.txt
```

3) Run the server
```
uvicorn src.api.main:app --reload --app-dir jira_mcp_backend/src --host 0.0.0.0 --port 8000
```

4) Generate OpenAPI
```
python -m src.api.generate_openapi --module-path jira_mcp_backend/src
```

## Environment Variables

See `.env.example` for all variables.

Key variables:
- AUTH_STRATEGY: "api_key" (default) or "jwt"
- API_KEY_HEADER_NAME: Header carrying the API key (default X-API-Key)
- API_KEYS: JSON list of allowed API keys, e.g. ["key1","key2"]
- JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN: JIRA credentials
- REQUEST_TIMEOUT_SECONDS: HTTP timeout

## Auth Usage

When AUTH_STRATEGY=api_key, include the key in the configured header:
```
-H "X-API-Key: your-key"
```

## Example cURL

- Health
```
curl http://localhost:8000/
```

- Get Issue
```
curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/jira/issues/ABC-1
```

- Create Issue
```
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: your-key" \
  -d '{"fields":{"project_key":"ABC","summary":"New","issuetype_name":"Task","description":"Body"}}' \
  http://localhost:8000/api/v1/jira/issues
```

- Transition Issue
```
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: your-key" \
  -d '{"transition_id":"31"}' \
  http://localhost:8000/api/v1/jira/issues/ABC-1/transitions
```

- Add Comment
```
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: your-key" \
  -d '{"body":"Hello"}' \
  http://localhost:8000/api/v1/jira/issues/ABC-1/comments
```

- Search
```
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: your-key" \
  -d '{"jql":"project=ABC","start_at":0,"max_results":10}' \
  http://localhost:8000/api/v1/jira/search
```

## OpenAPI

Run:
```
python jira_mcp_backend/src/api/generate_openapi.py
```
This writes `jira_mcp_backend/interfaces/openapi.json`.

## Notes

- JWT strategy is optional and not implemented in this default build.
- External JIRA calls are mocked in tests to avoid network access.