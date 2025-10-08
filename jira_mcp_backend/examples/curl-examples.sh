#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3001}"
API_KEY="${API_KEY:-change-me-strong-key}"
PROJECT_KEY="${PROJECT_KEY:-PROJ}"
BOARD_ID="${BOARD_ID:-123}"
SPRINT_ID="${SPRINT_ID:-456}"
ISSUE_KEY="${ISSUE_KEY:-PROJ-1}"
EPIC_KEY="${EPIC_KEY:-PROJ-101}"

hdr=(-H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json")

echo "Health:"
curl -s "${BASE_URL}/health" | jq .

echo
echo "Service info:"
curl -s "${BASE_URL}/" | jq .

echo
echo "JIRA Search (requires valid env configuration and API key):"
curl -s "${hdr[@]}" \
  --get "${BASE_URL}/jira/search" \
  --data-urlencode "jql=project=${PROJECT_KEY} ORDER BY created DESC" \
  --data-urlencode "max_results=5" | jq .

echo
echo "Create Issue (Task):"
curl -s "${hdr[@]}" -X POST "${BASE_URL}/jira/issue" \
  -d @- <<EOF | jq .
{
  "project_key": "${PROJECT_KEY}",
  "summary": "New task from curl example",
  "description": "Details here",
  "issuetype": "Task"
}
EOF

echo
echo "Create Epic:"
curl -s "${hdr[@]}" -X POST "${BASE_URL}/jira/epic" \
  -H "X-Idempotency-Key: $(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)" \
  -d @- <<EOF | jq .
{
  "project_key": "${PROJECT_KEY}",
  "epic_name": "Migration v2",
  "summary": "Epic via curl",
  "description": "Epic description"
}
EOF

echo
echo "Create Story (with story points and epic link):"
curl -s "${hdr[@]}" -X POST "${BASE_URL}/jira/story" \
  -H "X-Idempotency-Key: $(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)" \
  -d @- <<EOF | jq .
{
  "project_key": "${PROJECT_KEY}",
  "summary": "User can upload avatar",
  "description": "Details",
  "parent_epic_key": "${EPIC_KEY}",
  "story_points": 3
}
EOF

echo
echo "Link Issue to Epic:"
curl -s "${hdr[@]}" -X POST "${BASE_URL}/jira/epic/link" \
  -d @- <<EOF | jq .
{
  "epic_key_or_id": "${EPIC_KEY}",
  "issue_key_or_id": "${ISSUE_KEY}"
}
EOF

echo
echo "List Boards (optionally filtered by project):"
curl -s "${hdr[@]}" --get "${BASE_URL}/jira/boards" --data-urlencode "project_key_or_id=${PROJECT_KEY}" | jq .

echo
echo "List Sprints for Board:"
curl -s "${hdr[@]}" --get "${BASE_URL}/jira/boards/${BOARD_ID}/sprints" --data-urlencode "state=active" | jq .

echo
echo "Create Sprint:"
curl -s "${hdr[@]}" -X POST "${BASE_URL}/jira/sprints" \
  -H "X-Idempotency-Key: $(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)" \
  -d @- <<EOF | jq .
{
  "name": "Sprint from curl",
  "board_id": ${BOARD_ID},
  "start_date": "2025-01-10T09:00:00Z",
  "end_date": "2025-01-24T17:00:00Z",
  "goal": "Ship important features"
}
EOF

echo
echo "Update Sprint:"
curl -s "${hdr[@]}" -X PUT "${BASE_URL}/jira/sprints/${SPRINT_ID}" \
  -d @- <<EOF | jq .
{
  "name": "Sprint updated via curl",
  "goal": "Focus on defects"
}
EOF

echo
echo "Move Issues to Sprint:"
curl -s "${hdr[@]}" -X POST "${BASE_URL}/jira/sprints/${SPRINT_ID}/issues" \
  -d @- <<EOF | jq .
{
  "sprint_id": ${SPRINT_ID},
  "issue_keys": ["${ISSUE_KEY}"]
}
EOF

echo
echo "Get Sprint Issues:"
curl -s "${hdr[@]}" --get "${BASE_URL}/jira/sprints/${SPRINT_ID}/issues" \
  --data-urlencode "jql_filters=assignee=currentUser()" | jq .

echo
echo "Simple Issues via Params:"
curl -s "${hdr[@]}" --get "${BASE_URL}/jira/issues" \
  --data-urlencode "project=${PROJECT_KEY}" \
  --data-urlencode "sprint_id=${SPRINT_ID}" \
  --data-urlencode "status=To Do" | jq .

echo
echo "Get transitions then transition issue by name:"
transitions_json="$(curl -s "${hdr[@]}" --get "${BASE_URL}/jira/issues/${ISSUE_KEY}/transition")"
echo "${transitions_json}" | jq .
echo "Transition by name (if available):"
curl -s "${hdr[@]}" -X POST "${BASE_URL}/jira/issues/${ISSUE_KEY}/transition" \
  --get --data-urlencode "transition_name=Done" | jq .

echo
echo "Add Comment to Issue:"
curl -s "${hdr[@]}" -X POST "${BASE_URL}/jira/issues/${ISSUE_KEY}/comments" \
  --get --data-urlencode "body=Thanks for the update!" | jq .

echo
echo "Estimate Story Points:"
curl -s "${hdr[@]}" -X PUT "${BASE_URL}/jira/issues/${ISSUE_KEY}/estimate" \
  --get --data-urlencode "points=5" | jq .

echo
echo "Capacity Planning:"
curl -s -H "Content-Type: application/json" -X POST "${BASE_URL}/capacity/plan" \
  -d @- <<EOF | jq .
{
  "team_members": ["alice", "bob", "carol"],
  "sprint_days": 10,
  "hours_per_day": 6.5
}
EOF
