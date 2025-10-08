from fastapi.testclient import TestClient

from src.api.main import app


def test_health():
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "app" in data
