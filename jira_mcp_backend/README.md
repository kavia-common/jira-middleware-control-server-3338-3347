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
- Raw OpenAPI: `/openapi.json` (also exported to `interfaces/openapi.json`)

## Authentication and Headers

Secure endpoints require one of the following headers:
- `X-API-KEY: <your-key>`
- `Authorization: Bearer <your-key>`

Manage accepted keys via `APP_API_KEYS` (comma-separated) in `.env`.

Idempotency is best‑effort on select POST/PUT endpoints via:
- `X-Idempotency-Key: <uuid>`
The server forwards requests to JIRA which may not enforce idempotency for all routes. The header is accepted by these endpoints:
- POST `/jira/issue`
- POST `/jira/epic`
- POST `/jira/story`
- POST `/jira/sprints`
- POST `/jira/issues/{issueKey}/comments`

Every response includes a correlation `request_id` in the body and `X-Request-ID` header. You may pass your own `X-Request-ID` to propagate across systems.

## Rate Limits and Retry Behavior

This server implements resilient calling to JIRA:
- 429 Rate Limits: If JIRA returns HTTP 429, the client honors `Retry-After` (seconds). When absent or invalid, it uses exponential backoff (`JIRA_RETRY_BACKOFF_BASE` × 2^(attempt-1)). After exhausting `JIRA_RETRY_MAX_ATTEMPTS`, the server returns HTTP 429 with details.
- 5xx Errors: Retries with exponential backoff up to `JIRA_RETRY_MAX_ATTEMPTS`. If still failing, returns HTTP 502 with JIRA response text when available.
- 4xx Errors: 400/401/403/404 are forwarded with the same status. Other 4xx map to 400.

You can configure:
- `JIRA_TIMEOUT_SECONDS` (default 15)
- `JIRA_RETRY_MAX_ATTEMPTS` (default 3)
- `JIRA_RETRY_BACKOFF_BASE` (default 0.5)

## Error Model

All error responses include a structured payload:
```json
{
  "error": {
    "code": "unauthorized | jira_error | invalid_state | invalid_transition | missing_transition | empty_batch | batch_too_large | invalid_capacity_args | internal_server_error",
    "message": "Human-readable message",
    "details": { "optional": "JIRA text or context" }
  },
  "request_id": "req-..."
}
```

Common HTTP statuses:
- 400 Bad Request: validation errors, invalid state/transition, empty batches, batch too large, or mapped unknown 4xx from JIRA
- 401 Unauthorized: missing/invalid API key
- 404 Not Found: resources not found when proxied from JIRA
- 429 Too Many Requests: JIRA rate limiting exceeded
- 502 Bad Gateway: upstream JIRA 5xx or terminal client errors after retries
- 500 Internal Server Error: unexpected exception inside this server

## Endpoints with Examples

- `GET /` — service info
- `GET /health` — status, version, uptime

JIRA proxy:
- `GET /jira/search?jql=...&fields=summary,priority&max_results=25`  
  Response body matches `JiraSearchResponse` schema.

- `POST /jira/issue` — create issue  
  Request:
  ```json
  {
    "project_key": "PROJ",
    "summary": "New task",
    "description": "Details here",
    "issuetype": "Task"
  }
  ```
  Response:
  ```json
  {
    "issue": { "...": "JIRA issue payload" },
    "request_id": "req-..."
  }
  ```

Sprint ceremonies and related:
- `POST /jira/epic` — create an Epic (requires custom field "Epic Name")  
  Request:
  ```json
  {
    "project_key": "PROJ",
    "epic_name": "Migration v2",
    "summary": "Epic summary",
    "description": "Optional details"
  }
  ```
  Response envelope:
  ```json
  {
    "data": { "issue": { "...": "JIRA issue payload" } },
    "request_id": "req-..."
  }
  ```

- `POST /jira/story` — create a Story (optional epic link and story points)  
  Request:
  ```json
  {
    "project_key": "PROJ",
    "summary": "User can upload avatar",
    "description": "Details",
    "parent_epic_key": "PROJ-101",
    "story_points": 3
  }
  ```
  Response envelope same as Epic.

- `POST /jira/epic/link` — link issue to epic  
  Request:
  ```json
  { "epic_key_or_id": "PROJ-101", "issue_key_or_id": "PROJ-202" }
  ```
  Response:
  ```json
  {
    "data": { "ok": true, "issue": { "key_or_id": "PROJ-202" }, "updated_field": "customfield_..." },
    "request_id": "req-..."
  }
  ```

- `GET /jira/boards?project_key_or_id=PROJ` — list agile boards

- `GET /jira/boards/{boardId}/sprints?state=future|active|closed` — list sprints for board  
  Invalid `state` yields HTTP 400 with `invalid_state` error.

- `POST /jira/sprints` — create sprint  
  Request:
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
  Request (any subset):
  ```json
  { "name": "Sprint 34 (Updated)", "goal": "Finalize features" }
  ```

- `POST /jira/sprints/{sprintId}/issues` — move issues into sprint (max 100)  
  Request:
  ```json
  { "sprint_id": 456, "issue_keys": ["PROJ-11", "PROJ-12"] }
  ```
  Errors:
  - Empty list => 400 `empty_batch`
  - >100 issues => 400 `batch_too_large`

- `GET /jira/sprints/{sprintId}/issues?jql_filters=assignee=currentUser()` — sprint issues with optional JQL filters

- `GET /jira/issues?project=PROJ&assignee=jdoe&status=In%20Progress&sprint_id=456` — simple search via params

- `POST /jira/issues/{issueKey}/transition?transition_id=21` — transition issue  
  You may provide `transition_name` instead; unknown name => 400 `invalid_transition`. Missing both => 400 `missing_transition`.

- `POST /jira/issues/{issueKey}/comments?body=Thanks%20for%20the%20update!` — add a comment

- `PUT /jira/issues/{issueKey}/estimate?points=5` — set story points estimate

- `POST /capacity/plan` — compute team capacity  
  Request:
  ```json
  { "team_members": ["alice", "bob", "carol"], "sprint_days": 10, "hours_per_day": 6.5 }
  ```
  Response:
  ```json
  { "total_member_days": 30, "total_hours": 195.0, "request_id": "req-..." }
  ```
  Invalid args (<=0) => 400 `invalid_capacity_args`.

## Models

- CreateIssueRequest: `project_key` (str), `summary` (str), `description` (str, optional), `issuetype` (str)
- CreateEpicRequest: `project_key` (str), `epic_name` (str), `summary` (str), `description` (str, optional)
- CreateStoryRequest: `project_key` (str), `summary` (str), `description` (str, optional), `parent_epic_key` (str, optional), `story_points` (number, optional)
- LinkIssueToEpicRequest: `epic_key_or_id` (str), `issue_key_or_id` (str)
- CreateSprintRequest: `name` (str), `board_id` (int), `start_date` (ISO string, optional), `end_date` (ISO string, optional), `goal` (str, optional)
- UpdateSprintRequest: `name` (str, optional), `start_date` (ISO string, optional), `end_date` (ISO string, optional), `goal` (str, optional)
- MoveIssuesToSprintRequest: `sprint_id` (int), `issue_keys` (string[])
- JiraSearchResponse: `total` (int), `issues` (array<object>), `request_id` (str, optional)
- CapacityRequest: `team_members` (string[]), `sprint_days` (int), `hours_per_day` (number)
- CapacityResponse: `total_member_days` (int), `total_hours` (number), `request_id` (str, optional)

## Permissions and Custom Fields

- Agile endpoints (boards, sprints, sprint issues) require JIRA Software (Agile) permissions.
- Custom fields such as "Epic Link", "Epic Name", and "Story points" must exist in your JIRA instance. Their display names must match the configured values in `.env`:
  - `JIRA_STORY_POINTS_FIELD_NAME` (default "Story points")
  - `JIRA_EPIC_LINK_FIELD_NAME` (default "Epic Link")
  - `JIRA_EPIC_NAME_FIELD_NAME` (default "Epic Name")
- If your instance uses different display names, update these variables accordingly.

## Configuration

Pydantic settings live in `app/core/config.py`. Required env vars are validated on startup and missing values are logged as warnings. CORS is controlled via `APP_CORS_ORIGINS`.

Additional behavior controls:
- `JIRA_TIMEOUT_SECONDS` (default 15)
- `JIRA_RETRY_MAX_ATTEMPTS` (default 3)
- `JIRA_RETRY_BACKOFF_BASE` (default 0.5)
- `DEFAULT_TIMEZONE` (default "UTC")
- `DEFAULT_BOARD_ID` (optional integer)

See `.env.example` for the full set.

## Logging

Structured logging includes `request_id`, path, method, status_code, and duration. See `app/utils/logging.py`.

## Example Requests

See `examples/curl-examples.sh` for end-to-end examples with `BASE_URL` and `API_KEY`.

## Testing Guidance

- Access live docs at `/docs` and `/redoc`. The OpenAPI spec is exported to `interfaces/openapi.json`.
- Validate auth using either `X-API-KEY` or `Authorization: Bearer`.
- For POST/PUT calls, optionally include `X-Idempotency-Key` to protect against client retries.
- Observe rate limiting by inspecting 429 responses and `Retry-After` header. The client will already retry when talking to JIRA; callers should implement their own retry/backoff for 502/429 returned by this server.

## Notes

- The server is expected to run on port `3001` by the preview system.
- Ensure your API key is configured in `APP_API_KEYS`.
- Some operations may be constrained by project or board permissions in JIRA.
