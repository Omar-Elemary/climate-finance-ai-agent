"""Core service tests — real Week 3 engine, LLM boundary mocked.

Nothing here calls a paid/external LLM:
  - stub ``agent_factory`` drives the real DiscussionOrchestrator/GraphRouter.
  - the Week 1 RAG test uses a FakeLLM + the REAL RetrievalTool/corpus.
"""
from __future__ import annotations

import pytest

from agent_core import CoreDiscussionService, DiscussionRequest
from agent_core.exceptions import (
    AgentExecutionError,
    DiscussionExecutionError,
    DiscussionNotFound,
    InvalidDiscussionRequest,
)
from agent_core.schemas import (
    agents_view,
    messages_view,
    retrieval_context_view,
    rounds_view,
)


# ------------------------------------------------------------------ doubles


class StubPersona:
    def __init__(self, name: str) -> None:
        self.name = name


class StubAgent:
    """Minimal agent surface the orchestrator needs (respond/generate_opinion)."""

    def __init__(self, persona: StubPersona, stance_word: str = "support") -> None:
        self.persona = persona
        self._stance_word = stance_word
        self._calls = 0

    def respond(self, context: str) -> str:
        assert "DISCUSSION TOPIC" in context  # real context builder is used
        return f"{self.persona.name} responds with grounded analysis."

    def generate_opinion(self, topic: str) -> dict:
        self._calls += 1
        return {
            "opinion": (
                f"Round {self._calls}: {self.persona.name} {self._stance_word} "
                f"increased climate finance for '{topic}'. Bankable and feasible."
            ),
            "evidence": [f"evidence-chunk-{self._calls}"],
            "sources": ["https://example.com/source"],
        }


def make_core(**kwargs) -> CoreDiscussionService:
    from src.orchestration.persistence import InMemoryPersistence

    def agent_factory(persona):
        name = str(getattr(persona, "name", persona))
        stance = "oppose" if "policy" in name.lower() else "support"
        return StubAgent(StubPersona(name), stance_word=stance)

    kwargs.setdefault("persistence", InMemoryPersistence())
    kwargs.setdefault("agent_factory", agent_factory)
    return CoreDiscussionService(**kwargs)


# ------------------------------------------------------------------ basic


def test_core_accepts_discussion_request() -> None:
    core = make_core()
    state = core.create_discussion(DiscussionRequest(topic="Green hydrogen", num_rounds=1))
    assert state.discussion_id
    assert state.topic == "Green hydrogen"


def test_request_reuses_shared_config_model() -> None:
    from src.orchestration.models import DiscussionConfig

    config = DiscussionRequest(topic="x", num_rounds=2).to_config()
    assert isinstance(config, DiscussionConfig)
    assert config.num_rounds == 2
    assert config.enable_opinion_tracking is True


# ------------------------------------------------------------------ execution


def test_real_week1_retrieval_feeds_opinion_generation() -> None:
    """FakeLLM + REAL RetrievalTool + REAL corpus -> grounded opinion evidence."""
    from src.agent import Agent
    from src.personas import load_persona
    from src.tools import RetrievalTool

    class FakeLLM:
        provider_name = "fake"
        model = "fake-test"

        def generate(self, messages):
            from types import SimpleNamespace

            return SimpleNamespace(text="OPINION: support bankable finance. EVIDENCE: cited.")

    persona = load_persona("investor")  # real persona file
    tool = RetrievalTool()  # real Week 1 tool (BM25 path, no torch needed)
    agent = Agent(persona=persona, llm=FakeLLM(), tools=[tool])

    direct = tool.run(query="climate adaptation finance")
    assert direct.success, f"RAG failed: {direct.error}"
    assert direct.data and direct.data[0].get("chunk_text")
    assert direct.data[0].get("source_url")

    opinion = agent.generate_opinion("Should climate adaptation finance increase?")
    assert opinion["evidence"], "Week 1 evidence did not reach the opinion"
    assert opinion["sources"], "Week 1 sources did not reach the opinion"


def test_rag_failure_degrades_honestly_without_crashing() -> None:
    """A failing retrieval tool yields empty evidence — never fake evidence."""
    from src.agent import Agent
    from src.personas import load_persona
    from src.tools.base import Tool, ToolResult

    class BrokenRetrieval(Tool):
        name = "climate_knowledge_search"
        description = "broken"

        def run(self, **kwargs) -> ToolResult:
            return ToolResult(success=False, error="boom")

    class FakeLLM:
        provider_name = "fake"
        model = "fake-test"

        def generate(self, messages):
            from types import SimpleNamespace

            return SimpleNamespace(text="neutral opinion without cues xyzzy.")

    agent = Agent(
        persona=load_persona("scientist"), llm=FakeLLM(), tools=[BrokenRetrieval()]
    )
    opinion = agent.generate_opinion("Some topic without retrieval")
    assert opinion["evidence"] == []
    assert opinion["opinion"]  # generation still works


# ------------------------------------------------------------------ rounds/result


def test_discussion_produces_at_least_three_rounds() -> None:
    core = make_core()
    state = core.create_discussion(
        DiscussionRequest(topic="Financing green hydrogen", num_rounds=3)
    )
    d = state.to_dict()
    assert state.current_round == 3
    rounds = rounds_view(state)
    assert [r["round"] for r in rounds] == [1, 2, 3]
    assert all(r["messages"] for r in rounds)
    assert len(d["messages"]) >= 3 * 3  # fan-out: >= agents x rounds


def test_result_contains_required_contract_fields() -> None:
    core = make_core()
    state = core.create_discussion(
        DiscussionRequest(
            topic="Should fossil fuel subsidies be eliminated?",
            num_rounds=2,
            personas=["investor", "policy_expert"],
        )
    )
    d = state.to_dict()
    assert d["discussion_id"] and d["topic"].startswith("Should fossil")
    assert agents_view(state)  # agents
    assert rounds_view(state)  # rounds
    assert messages_view(state)  # messages
    assert retrieval_context_view(state)  # retrieval_context
    assert set(d["opinions"].keys()) == set(d["participants"])
    assert d["status"] == "completed"


def test_retrieval_roundtrip_through_backend_shape() -> None:
    """GET-equivalent: re-load by id preserves opinions + retrieval context."""
    core = make_core()
    created = core.create_discussion(DiscussionRequest(topic="Solar ROI", num_rounds=2))
    loaded = core.get_discussion(created.discussion_id)
    assert loaded.to_dict() == created.to_dict()
    ctx = retrieval_context_view(loaded)[0]
    assert ctx["opinion_citations"]
    assert all("evidence" in c and "sources" in c for c in ctx["opinion_citations"])


# ------------------------------------------------------------------ metadata


def test_metadata_preserved_agent_round_recipient_retrieval() -> None:
    core = make_core()
    state = core.create_discussion(
        DiscussionRequest(topic="Green bonds impact", num_rounds=2)
    )
    msgs = messages_view(state)
    assert msgs
    for m in msgs:
        assert m["message_id"] and m["agent_id"] and m["round"] and m["content"]
    # GraphRouter fans each message out with recipient_id metadata.
    assert any(m["recipient_id"] for m in msgs), "routing metadata was lost"
    ctx = retrieval_context_view(state)[0]
    assert ctx["opinion_citations"], "opinion evidence/sources were lost"


def test_analytics_compatibility_run_analytics_still_works() -> None:
    from src.analytics import run_analytics

    core = make_core()
    state = core.create_discussion(
        DiscussionRequest(topic="Just transition finance", num_rounds=2)
    )
    report = run_analytics(state)
    assert report.is_valid
    payload = report.to_dict()
    assert payload["metrics"]["opinion"]["status"] == "ok"
    assert payload["metrics"]["agreement"]["status"] == "ok"
    assert payload["metrics"]["influence"]["status"] == "ok"


# ------------------------------------------------------------------ errors


@pytest.mark.parametrize("topic", ["", "   ", None])
def test_invalid_topic_rejected(topic) -> None:
    core = make_core()
    with pytest.raises(InvalidDiscussionRequest):
        core.create_discussion(DiscussionRequest(topic=topic, num_rounds=1))


@pytest.mark.parametrize("num_rounds", [0, -1, 99, "3", True])
def test_invalid_num_rounds_rejected(num_rounds) -> None:
    core = make_core()
    with pytest.raises(InvalidDiscussionRequest):
        core.create_discussion(
            DiscussionRequest(topic="x", num_rounds=num_rounds)  # type: ignore[arg-type]
        )


def test_unknown_persona_rejected() -> None:
    core = make_core()
    with pytest.raises(InvalidDiscussionRequest):
        core.create_discussion(
            DiscussionRequest(topic="x", num_rounds=1, personas=["no_such_persona"])
        )


def test_duplicate_personas_rejected() -> None:
    core = make_core()
    with pytest.raises(InvalidDiscussionRequest):
        core.create_discussion(
            DiscussionRequest(
                topic="x", num_rounds=1, personas=["investor", "investor"]
            )
        )


def test_non_request_object_rejected() -> None:
    core = make_core()
    with pytest.raises(InvalidDiscussionRequest):
        core.create_discussion({"topic": "x"})  # type: ignore[arg-type]


def test_unknown_discussion_id_not_found() -> None:
    core = make_core()
    with pytest.raises(DiscussionNotFound):
        core.get_discussion("does-not-exist")


def test_empty_discussion_id_rejected() -> None:
    core = make_core()
    with pytest.raises(InvalidDiscussionRequest):
        core.get_discussion("  ")


def test_agent_factory_failure_is_agent_error() -> None:
    from src.orchestration.persistence import InMemoryPersistence

    def broken_factory(persona):
        raise RuntimeError("LLM down")

    core = CoreDiscussionService(
        persistence=InMemoryPersistence(), agent_factory=broken_factory
    )
    with pytest.raises(AgentExecutionError):
        core.create_discussion(DiscussionRequest(topic="x", num_rounds=1))


def test_llm_provider_failure_is_agent_error() -> None:
    from src.orchestration.persistence import InMemoryPersistence

    def broken_llm():
        raise ValueError("No API key found")

    core = CoreDiscussionService(
        persistence=InMemoryPersistence(), llm_provider_factory=broken_llm
    )
    with pytest.raises(AgentExecutionError):
        core.create_discussion(DiscussionRequest(topic="x", num_rounds=1))


def test_broken_persistence_is_execution_error() -> None:
    class BrokenPersistence:
        def save(self, state) -> None:
            raise RuntimeError("disk down")

        def load(self, discussion_id: str):
            raise RuntimeError("disk down")

    core = make_core(persistence=BrokenPersistence())
    with pytest.raises(DiscussionExecutionError):
        core.create_discussion(DiscussionRequest(topic="x", num_rounds=1))
    with pytest.raises(DiscussionExecutionError):
        core.get_discussion("anything")
