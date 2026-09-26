"""Shared pytest fixtures — stub Core Agent (no LLM, no network)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.dependencies import get_analytics_service, get_discussion_service
from backend.app.main import create_app
from backend.app.services.analytics_service import AnalyticsService
from backend.app.services.discussion_service import DiscussionService


class StubPersona:
    def __init__(self, name: str) -> None:
        self.name = name


class StubAgent:
    """Minimal Core Agent surface: respond() + generate_opinion()."""

    def __init__(self, persona: StubPersona, stance_word: str = "support") -> None:
        self.persona = persona
        self._stance_word = stance_word
        self._calls = 0

    def respond(self, context: str) -> str:
        _ = context
        return f"{self.persona.name} responds with grounded analysis."

    def generate_opinion(self, topic: str) -> dict:
        self._calls += 1
        return {
            "opinion": (
                f"Round {self._calls}: {self.persona.name} {self._stance_word} "
                f"increased climate finance for '{topic}'. Bankable and feasible."
            ),
            "evidence": [f"evidence-{self._calls}"],
            "sources": ["https://example.com/source"],
        }


def make_stub_service(**kwargs) -> DiscussionService:
    from src.orchestration.persistence import InMemoryPersistence

    def agent_factory(persona):
        name = getattr(persona, "name", "")
        # Give one agent an opposing cue so agreement < 1.0 and influence varies.
        stance = "oppose" if "policy" in str(name).lower() else "support"
        return StubAgent(StubPersona(str(name)), stance_word=stance)

    return DiscussionService(
        persistence=InMemoryPersistence(), agent_factory=agent_factory, **kwargs
    )


@pytest.fixture()
def stub_service() -> DiscussionService:
    return make_stub_service()


@pytest.fixture()
def client(stub_service: DiscussionService) -> TestClient:
    app = create_app()
    analytics = AnalyticsService(stub_service)

    def _override_discussions() -> DiscussionService:
        return stub_service

    def _override_analytics() -> AnalyticsService:
        return analytics

    app.dependency_overrides[get_discussion_service] = _override_discussions
    app.dependency_overrides[get_analytics_service] = _override_analytics
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def discussion_id(client: TestClient) -> str:
    resp = client.post(
        "/discussions",
        json={"topic": "Financing green hydrogen", "num_rounds": 2},
    )
    assert resp.status_code == 202, resp.text
    return resp.json()["discussion_id"]
