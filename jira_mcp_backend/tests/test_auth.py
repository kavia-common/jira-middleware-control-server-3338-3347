import os

from fastapi.testclient import TestClient

os.environ["AUTH_STRATEGY"] = "api_key"
os.environ["API_KEY_HEADER_NAME"] = "X-API-Key"
os.environ["API_KEYS"] = '["test-key"]'  # pydantic settings can parse env JSON lists
os.environ["JIRA_BASE_URL"] = "https://example.atlassian.net"
os.environ["JIRA_EMAIL"] = "user@example.com"
os.environ["JIRA_API_TOKEN"] = "token"

from src.api.main import app  # noqa: E402

client = TestClient(app)


def test_auth_missing_key():
    r = client.get("/api/v1/jira/issues/ABC-1")
    assert r.status_code in (401, 422)  # 401 expected, 422 may occur if router evaluated dependency differently


def test_auth_with_key(monkeypatch):
    # Mock JiraClient get_issue to avoid external call
    from src.clients.jira_client import JiraClient

    async def fake_open(self):  # noqa: D401
        self._client = True  # sentinel

    async def fake_get_issue(self, issue_key, fields=None):
        return {"id": "100", "key": issue_key, "fields": {}}

    async def fake_close(self):
        self._client = None

    monkeypatch.setattr(JiraClient, "open", fake_open)
    monkeypatch.setattr(JiraClient, "get_issue", fake_get_issue)
    monkeypatch.setattr(JiraClient, "close", fake_close)

    r = client.get("/api/v1/jira/issues/ABC-1", headers={"X-API-Key": "test-key"})
    assert r.status_code == 200
    assert r.json()["key"] == "ABC-1"
