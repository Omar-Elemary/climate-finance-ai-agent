"""Health + topics contract tests."""
from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_topics_returns_valid_list(client: TestClient) -> None:
    resp = client.get("/topics")
    assert resp.status_code == 200
    topics = resp.json()
    assert isinstance(topics, list) and len(topics) >= 1
    for topic in topics:
        assert topic["id"]
        assert topic["title"]
        assert topic["domain"]
