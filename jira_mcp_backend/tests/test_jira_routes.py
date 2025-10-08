import os

from fastapi.testclient import TestClient

# Set minimal env for settings
os.environ["AUTH_STRATEGY"] = "api_key"
os.environ["API_KEY_HEADER_NAME"] = "X-API-Key"
os.environ["API_KEYS"] = '["test-key"]'
os.environ["JIRA_BASE_URL"] = "https://example.atlassian.net"
os.environ["JIRA_EMAIL"] = "user@example.com"
os.environ["JIRA_API_TOKEN"] = "token"

from src.api.main import app  # noqa: E402

client = TestClient(app)
HEADERS = {"X-API-Key": "test-key"}


def test_get_issue(monkeypatch):
    from src.clients.jira_client import JiraClient

    async def fake_open(self):  # noqa: D401
        self._client = True

    async def fake_close(self):
        self._client = None

    async def fake_get_issue(self, issue_key, fields=None):
        return {"id": "101", "key": issue_key, "fields": {"summary": "Test"}}

    monkeypatch.setattr(JiraClient, "open", fake_open)
    monkeypatch.setattr(JiraClient, "close", fake_close)
    monkeypatch.setattr(JiraClient, "get_issue", fake_get_issue)

    r = client.get("/api/v1/jira/issues/ABC-2", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["key"] == "ABC-2"


def test_create_issue(monkeypatch):
    from src.clients.jira_client import JiraClient

    async def fake_open(self):  # noqa: D401
        self._client = True

    async def fake_close(self):
        self._client = None

    async def fake_create_issue(self, project_key, summary, issuetype_name, description=None):
        return {"id": "200", "key": "ABC-200", "self": "url"}

    monkeypatch.setattr(JiraClient, "open", fake_open)
    monkeypatch.setattr(JiraClient, "close", fake_close)
    monkeypatch.setattr(JiraClient, "create_issue", fake_create_issue)

    payload = {
        "fields": {
            "project_key": "ABC",
            "summary": "New Issue",
            "issuetype_name": "Task",
            "description": "Body",
        }
    }
    r = client.post("/api/v1/jira/issues", json=payload, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["key"] == "ABC-200"


def test_transition_issue(monkeypatch):
    from src.clients.jira_client import JiraClient

    async def fake_open(self):  # noqa: D401
        self._client = True

    async def fake_close(self):
        self._client = None

    async def fake_transition_issue(self, issue_key, transition_id):
        return None

    monkeypatch.setattr(JiraClient, "open", fake_open)
    monkeypatch.setattr(JiraClient, "close", fake_close)
    monkeypatch.setattr(JiraClient, "transition_issue", fake_transition_issue)

    payload = {"transition_id": "31"}
    r = client.post("/api/v1/jira/issues/ABC-3/transitions", json=payload, headers=HEADERS)
    assert r.status_code == 204


def test_add_comment(monkeypatch):
    from src.clients.jira_client import JiraClient

    async def fake_open(self):  # noqa: D401
        self._client = True

    async def fake_close(self):
        self._client = None

    async def fake_add_comment(self, issue_key, body):
        return {"id": "301", "body": body}

    monkeypatch.setattr(JiraClient, "open", fake_open)
    monkeypatch.setattr(JiraClient, "close", fake_close)
    monkeypatch.setattr(JiraClient, "add_comment", fake_add_comment)

    payload = {"body": "Hello world"}
    r = client.post("/api/v1/jira/issues/ABC-4/comments", json=payload, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["data"]["id"] == "301"


def test_search(monkeypatch):
    from src.clients.jira_client import JiraClient

    async def fake_open(self):  # noqa: D401
        self._client = True

    async def fake_close(self):
        self._client = None

    async def fake_search(self, jql, start_at=0, max_results=50, fields=None):
        return {"startAt": 0, "maxResults": 1, "total": 1, "issues": [{"id": "1", "key": "ABC-1", "fields": {}}]}

    monkeypatch.setattr(JiraClient, "open", fake_open)
    monkeypatch.setattr(JiraClient, "close", fake_close)
    monkeypatch.setattr(JiraClient, "search", fake_search)

    payload = {"jql": "project=ABC", "start_at": 0, "max_results": 1}
    r = client.post("/api/v1/jira/search", json=payload, headers=HEADERS)
    assert r.status_code == 200
    assert "data" in r.json()
