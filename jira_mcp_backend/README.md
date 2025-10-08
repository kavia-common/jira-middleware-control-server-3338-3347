# JIRA MCP Backend

A Python-based MCP (Middleware Control Point) server for JIRA, built with FastAPI. It proxies authorized requests to the JIRA REST API.

## Features
- FastAPI app with CORS, request ID middleware, and structured logging
- Simple API key authentication via `X-API-KEY` or `Authorization: Bearer`
- Health and root endpoints
- JIRA search and create issue endpoints
- Sprint ceremonies endpoints: epics/stories, boards/sprints, transitions, comments, estimates, capacity planning
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
- Optionally adjust retry/timeout and custom field names if your instance differs

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

## Authentication

Secure endpoints require one of the following headers:
- `X-API-KEY: <your-key>`
- `Authorization: Bearer <your-key>`

Manage accepted keys via `APP_API_KEYS` (comma-separated) in `.env`.

Idempotency is supported on select POST/PUT endpoints via:
- `X-Idempotency-Key: <uuid>` (best-effort; requests are proxied to JIRA which may not enforce it for all routes)

Each response includes `request_id` for tracing and returns `X-Request-ID` in headers.

## Endpoints

- `GET /` — service info
- `GET /health` — status, version, uptime

Core JIRA proxy:
- `GET /jira/search?jql=...&fields=summary,priority&max_results=25`
- `POST /jira/issue` — create issue:
```json
{
  "project_key": "PROJ",
  "summary": "New task",
  "description": "Details here",
  "issuetype": "Task"
}
```

Sprint ceremonies and related:
- `POST /jira/epic` — create an Epic (requires custom field "Epic Name")
  - Request:
  ```json
  {
    "project_key": "PROJ",
    "epic_name": "Migration v2",
    "summary": "Epic summary",
    "description": "Optional details"
  }
  ```
- `POST /jira/story` — create a Story (optional epic link and story points)
  - Request:
  ```json
  {
    "project_key": "PROJ",
    "summary": "User can upload avatar",
    "description": "Details",
    "parent_epic_key": "PROJ-101",
    "story_points": 3
  }
  ```
- `POST /jira/epic/link` — link issue to epic (sets Epic Link custom field)
  - Request:
  ```json
  {
    "epic_key_or_id": "PROJ-101",
    "issue_key_or_id": "PROJ-202"
  }
  ```
- `GET /jira/boards?project_key_or_id=PROJ` — list agile boards (requires JIRA Agile permissions)
- `GET /jira/boards/{boardId}/sprints?state=future|active|closed` — list sprints for board
- `POST /jira/sprints` — create sprint
  - Request:
  ```json
  {
    "name": "Sprint 34",
    "board_id": 123,
    "start_date": "2025-01-10T09:00:00Z",
    "end_date": "2025-01-24T17:00:00Z",
    "goal": "Complete authentication refactor"
  }
  ```
- `PUT /jira/sprints/{sprintId}` — update sprint (partial)
  - Request (any subset):
  ```json
  {
    "name": "Sprint 34 (Updated)",
    "start_date": "2025-01-10T09:00:00Z",
    "end_date": "2025-01-24T17:00:00Z",
    "goal": "Finalize features"
  }
  ```
- `POST /jira/sprints/{sprintId}/issues` — move issues into sprint (max 100)
  - Request:
  ```json
  {
    "sprint_id": 456,
    "issue_keys": ["PROJ-11", "PROJ-12"]
  }
  ```
- `GET /jira/sprints/{sprintId}/issues?jql_filters=assignee=currentUser()` — get sprint issues with optional extra JQL
- `GET /jira/issues?project=PROJ&assignee=jdoe&status=In%20Progress&sprint_id=456` — simple filtered search via params
- `POST /jira/issues/{issueKey}/transition?transition_id=21` — transition issue (or provide `transition_name` instead of id)
- `POST /jira/issues/{issueKey}/comments?body=Thanks%20for%20the%20update!` — add a comment
- `PUT /jira/issues/{issueKey}/estimate?points=5` — set story points estimate (custom field mapping)
- `POST /capacity/plan` — compute team capacity
  - Request:
  ```json
  {
    "team_members": ["alice", "bob", "carol"],
    "sprint_days": 10,
    "hours_per_day": 6.5
  }
  ```
  - Response:
  ```json
  {
    "total_member_days": 30,
    "total_hours": 195.0,
    "request_id": "req-..."
  }
  ```

## Permissions and Custom Fields

- Agile endpoints (boards, sprints, sprint issues) require JIRA Software (Agile) permissions.
- Custom fields such as "Epic Link", "Epic Name", and "Story points" must exist in your JIRA instance. Their display names must match the configured values in `.env`:
  - `JIRA_STORY_POINTS_FIELD_NAME` (default "Story points")
  - `JIRA_EPIC_LINK_FIELD_NAME` (default "Epic Link")
  - `JIRA_EPIC_NAME_FIELD_NAME` (default "Epic Name")
- If your instance uses different display names, update these variables accordingly.

## Configuration

Pydantic settings are defined in `app/core/config.py`. Required env vars for JIRA are validated at startup (warnings logged if missing). CORS can be controlled via `APP_CORS_ORIGINS`.

Additional client behavior controls:
- `JIRA_TIMEOUT_SECONDS` (default 15)
- `JIRA_RETRY_MAX_ATTEMPTS` (default 3)
- `JIRA_RETRY_BACKOFF_BASE` (default 0.5)
- `DEFAULT_TIMEZONE` (default "UTC")
- `DEFAULT_BOARD_ID` (optional integer)

See `.env.example` for the full set.

## Logging

Logging is configured in `app/utils/logging.py` and includes request_id, path, method, status_code, and duration in structured logs.

## Examples

The repo includes `examples/curl-examples.sh` with ready-to-run commands using `BASE_URL` and `API_KEY` environment variables.

## Notes

- The server is expected to run on port `3001` by the preview system.
- Ensure your API key is configured in `APP_API_KEYS`.
- Some operations may be constrained by project or board permissions in JIRA.
