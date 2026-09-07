"""
Tests for Discussion Orchestration (Member 2 responsibility).

All external components (agents, routers, retrievers, persistence) are mocked.
These tests verify the orchestrator's behavior, not the internals of
components owned by other members.
"""

from unittest.mock import MagicMock, patch
import pytest

from src.orchestration.models import (
    DiscussionConfig,
    DiscussionResult,
    DiscussionState,
    DiscussionStatus,
    Message,
    OpinionRecord,
    RetrievalEvent,
)
from src.orchestration.context import DiscussionContextBuilder
from src.orchestration.scheduler import SequentialScheduler
from src.orchestration.termination import MaxRoundsTermination
from src.orchestration.persistence import InMemoryPersistence
from src.orchestration.router import PassthroughRouter
from src.orchestration.orchestrator import DiscussionOrchestrator


# ---------------------------------------------------------------------------
# Helpers — mock agent that behaves like the Week 2 Agent
# ---------------------------------------------------------------------------

class MockPersona:
    """Minimal mock for src.personas.base.Persona."""

    def __init__(self, name: str):
        self.name = name

    def to_prompt_context(self) -> str:
        return f"You are: {self.name}"


class MockAgent:
    """
    Mock agent that mimics the Week 2 Agent interface.

    Responds with a deterministic message based on persona name and round.
    Tracks calls for assertion.
    """

    def __init__(self, persona_name: str):
        self.persona = MockPersona(persona_name)
        self.respond_calls: list[str] = []
        self.opinion_calls: list[str] = []

    def respond(self, message: str) -> str:
        self.respond_calls.append(message)
        return f"Response from {self.persona.name}: I have considered the context."

    def generate_opinion(self, topic: str) -> dict:
        self.opinion_calls.append(topic)
        return {
            "topic": topic,
            "persona": self.persona.name,
            "opinion": f"{self.persona.name} opinion on {topic}",
            "evidence": ["evidence chunk 1"],
            "sources": ["https://example.com"],
        }


class MockRetriever:
    """Mock retriever that returns deterministic results."""

    def __init__(self, results: list[dict] | None = None):
        self._results = results or [
            {"chunk_text": "Climate finance increased by 15%", "source_url": "https://example.com/report"}
        ]
        self.retrieve_calls: list[dict] = []

    def retrieve(self, query: str, top_k: int = 3, **kwargs) -> list[dict]:
        self.retrieve_calls.append({"query": query, "top_k": top_k})
        return self._results[:top_k]


class MockRouter:
    """Mock router that records calls and passes messages through."""

    def __init__(self):
        self.route_calls: list[dict] = []

    def route(self, message: dict, graph=None, state=None) -> list[dict]:
        self.route_calls.append(message)
        return [message]


# ---------------------------------------------------------------------------
# Test 1 — Discussion initialization
# ---------------------------------------------------------------------------

def test_discussion_initialization():
    """Verify unique discussion ID, correct topic, participants registered, initial state."""
    orchestrator = DiscussionOrchestrator()
    agents = [MockAgent("Investor"), MockAgent("Scientist")]

    result = orchestrator.start_discussion(
        topic="Climate finance topic",
        agents=agents,
        config=DiscussionConfig(num_rounds=1),
    )

    assert result.discussion_id is not None
    assert isinstance(result.discussion_id, str)
    assert len(result.discussion_id) > 0
    assert result.topic == "Climate finance topic"
    assert "investor" in result.participants
    assert "scientist" in result.participants
    assert result.status == DiscussionStatus.COMPLETED


# ---------------------------------------------------------------------------
# Test 2 — Three-round execution
# ---------------------------------------------------------------------------

def test_three_round_execution():
    """Verify 3 rounds execute with correct round numbers."""
    orchestrator = DiscussionOrchestrator()
    agents = [MockAgent("A"), MockAgent("B")]

    result = orchestrator.start_discussion(
        topic="Test topic",
        agents=agents,
        config=DiscussionConfig(num_rounds=3),
    )

    assert result.rounds_completed == 3

    # Each round should have messages from both agents
    round_numbers = set(m.round for m in result.messages)
    assert round_numbers == {1, 2, 3}

    # 3 rounds x 2 agents = 6 messages
    assert len(result.messages) == 6


# ---------------------------------------------------------------------------
# Test 3 — Agent participation
# ---------------------------------------------------------------------------

def test_agent_participation():
    """Verify multiple agents participate in the discussion."""
    orchestrator = DiscussionOrchestrator()
    agent_a = MockAgent("Investor")
    agent_b = MockAgent("Scientist")
    agent_c = MockAgent("Policy Expert")

    result = orchestrator.start_discussion(
        topic="Multi-agent test",
        agents=[agent_a, agent_b, agent_c],
        config=DiscussionConfig(num_rounds=2),
    )

    # All 3 agents should have been called
    assert len(agent_a.respond_calls) == 2
    assert len(agent_b.respond_calls) == 2
    assert len(agent_c.respond_calls) == 2

    # Messages should reference all agents
    agent_names = {m.agent_name for m in result.messages}
    assert "Investor" in agent_names
    assert "Scientist" in agent_names
    assert "Policy Expert" in agent_names


# ---------------------------------------------------------------------------
# Test 4 — Context propagation
# ---------------------------------------------------------------------------

def test_context_propagation():
    """Verify Round 2 receives Round 1 context and Round 3 receives earlier history."""
    orchestrator = DiscussionOrchestrator()
    agent = MockAgent("Agent1")

    result = orchestrator.start_discussion(
        topic="Context test",
        agents=[agent],
        config=DiscussionConfig(num_rounds=3),
    )

    # Agent was called 3 times (once per round)
    assert len(agent.respond_calls) == 3

    # Round 1 context should NOT contain discussion history
    round1_context = agent.respond_calls[0]
    assert "DISCUSSION HISTORY" not in round1_context
    assert "Context test" in round1_context

    # Round 2 context should contain Round 1 message
    round2_context = agent.respond_calls[1]
    assert "DISCUSSION HISTORY" in round2_context
    assert "Response from Agent1" in round2_context

    # Round 3 context should contain messages from rounds 1 and 2
    round3_context = agent.respond_calls[2]
    assert "DISCUSSION HISTORY" in round3_context


# ---------------------------------------------------------------------------
# Test 5 — Routing integration
# ---------------------------------------------------------------------------

def test_routing_integration():
    """Mock the router and verify the orchestrator invokes it for agent responses."""
    mock_router = MockRouter()
    orchestrator = DiscussionOrchestrator(router=mock_router)
    agent = MockAgent("TestAgent")

    result = orchestrator.start_discussion(
        topic="Routing test",
        agents=[agent],
        config=DiscussionConfig(num_rounds=2),
    )

    # Router should have been called once per agent per round
    assert len(mock_router.route_calls) == 2

    # Each route call should contain agent_id and content
    for call in mock_router.route_calls:
        assert "agent_id" in call
        assert "content" in call
        assert "round" in call


# ---------------------------------------------------------------------------
# Test 6 — Retrieval integration
# ---------------------------------------------------------------------------

def test_retrieval_integration():
    """Mock the retriever and verify retrieval can occur during discussion."""
    mock_retriever = MockRetriever()
    orchestrator = DiscussionOrchestrator(retriever=mock_retriever)
    agent = MockAgent("Agent1")

    result = orchestrator.start_discussion(
        topic="Retrieval test",
        agents=[agent],
        config=DiscussionConfig(num_rounds=2, enable_retrieval=True),
    )

    # Retriever should have been called (once per round for the agent)
    assert len(mock_retriever.retrieve_calls) == 2

    # Retrieval events should be recorded
    assert len(result.retrieval_events) == 2
    for event in result.retrieval_events:
        assert event.discussion_id == result.discussion_id
        assert event.round in {1, 2}
        assert len(event.results) > 0


# ---------------------------------------------------------------------------
# Test 7 — Opinion history
# ---------------------------------------------------------------------------

def test_opinion_history():
    """Verify opinions are preserved across all rounds rather than overwritten."""
    orchestrator = DiscussionOrchestrator()
    agent = MockAgent("OpinionAgent")

    result = orchestrator.start_discussion(
        topic="Opinion test",
        agents=[agent],
        config=DiscussionConfig(num_rounds=3, enable_opinion_tracking=True),
    )

    # Agent should have generated opinions for each round
    assert len(agent.opinion_calls) == 3

    # Opinion records should exist for each round
    agent_id = "opinionagent"
    assert agent_id in result.opinions
    opinion_records = result.opinions[agent_id]
    assert len(opinion_records) == 3

    # Each record should have a different round
    rounds = [r.round for r in opinion_records]
    assert rounds == [1, 2, 3]

    # Previous opinions should NOT be overwritten
    for record in opinion_records:
        assert record.opinion  # non-empty


# ---------------------------------------------------------------------------
# Test 8 — Persistence
# ---------------------------------------------------------------------------

def test_persistence():
    """Mock persistence and verify state is saved after expected checkpoints."""
    mock_persistence = MagicMock()
    orchestrator = DiscussionOrchestrator(persistence=mock_persistence)
    agent = MockAgent("PersistAgent")

    result = orchestrator.start_discussion(
        topic="Persistence test",
        agents=[agent],
        config=DiscussionConfig(num_rounds=3),
    )

    # Persistence should be called:
    # 1 (init) + 3 (after each round) + 1 (final) = 5
    assert mock_persistence.save.call_count == 5

    # Each saved state should have the correct discussion_id
    for call in mock_persistence.save.call_args_list:
        saved_state = call[0][0]
        assert saved_state.discussion_id == result.discussion_id


# ---------------------------------------------------------------------------
# Test 9 — Termination
# ---------------------------------------------------------------------------

def test_termination():
    """Verify the orchestrator stops exactly at the configured number of rounds."""
    orchestrator = DiscussionOrchestrator()
    agents = [MockAgent("A"), MockAgent("B")]

    # Run with 1 round
    result_1 = orchestrator.start_discussion(
        topic="Termination test 1",
        agents=agents,
        config=DiscussionConfig(num_rounds=1),
    )
    assert result_1.rounds_completed == 1
    assert len(result_1.messages) == 2  # 1 round x 2 agents

    # Run with 5 rounds
    result_5 = orchestrator.start_discussion(
        topic="Termination test 5",
        agents=agents,
        config=DiscussionConfig(num_rounds=5),
    )
    assert result_5.rounds_completed == 5
    assert len(result_5.messages) == 10  # 5 rounds x 2 agents


# ---------------------------------------------------------------------------
# Test 10 — Reproducibility
# ---------------------------------------------------------------------------

def test_reproducibility():
    """Use deterministic agents and verify same config produces same sequence."""
    orchestrator = DiscussionOrchestrator()

    def run_discussion():
        agents = [MockAgent("Alpha"), MockAgent("Beta")]
        return orchestrator.start_discussion(
            topic="Reproducibility test",
            agents=agents,
            config=DiscussionConfig(num_rounds=2),
        )

    result1 = run_discussion()
    result2 = run_discussion()

    # Different discussion IDs (UUIDs)
    assert result1.discussion_id != result2.discussion_id

    # Same structure
    assert result1.topic == result2.topic
    assert result1.participants == result2.participants
    assert result1.rounds_completed == result2.rounds_completed
    assert len(result1.messages) == len(result2.messages)
    assert len(result1.opinions) == len(result2.opinions)

    # Same message sequence (content is deterministic from MockAgent)
    for m1, m2 in zip(result1.messages, result2.messages):
        assert m1.agent_name == m2.agent_name
        assert m1.round == m2.round
        assert m1.content == m2.content


# ---------------------------------------------------------------------------
# Additional tests — Model serialization
# ---------------------------------------------------------------------------

def test_discussion_result_to_dict():
    """Verify DiscussionResult serializes to a dict."""
    orchestrator = DiscussionOrchestrator()
    agent = MockAgent("Agent1")

    result = orchestrator.start_discussion(
        topic="Serialization test",
        agents=[agent],
        config=DiscussionConfig(num_rounds=1),
    )

    d = result.to_dict()
    assert isinstance(d, dict)
    assert d["discussion_id"] == result.discussion_id
    assert d["topic"] == "Serialization test"
    assert d["status"] == "completed"
    assert isinstance(d["messages"], list)
    assert isinstance(d["opinions"], dict)
    assert isinstance(d["retrieval_events"], list)


def test_context_builder_bounded_messages():
    """Verify context builder respects max_messages limit."""
    builder = DiscussionContextBuilder(max_messages=2)
    state = DiscussionState(
        discussion_id="test",
        topic="Topic",
        current_round=5,
        total_rounds=5,
    )
    # Add 5 messages from rounds 1-4 (previous rounds before round 5)
    for i in range(1, 5):
        state.add_message(Message(
            message_id=f"m{i}",
            discussion_id="test",
            round=i,
            agent_id="a1",
            agent_name="Agent1",
            content=f"Message {i}",
        ))

    context = builder.build(agent_id="a1", agent_name="Agent1", state=state)

    # Context builder shows messages from rounds BEFORE current round (1-4),
    # bounded to last max_messages=2. So should show rounds 3 and 4 only.
    assert "Message 3" in context
    assert "Message 4" in context
    assert "Message 1" not in context
    assert "Message 2" not in context


def test_in_memory_persistence():
    """Verify InMemoryPersistence stores and retrieves correctly."""
    persistence = InMemoryPersistence()
    state = DiscussionState(discussion_id="test-123", topic="Topic")

    assert persistence.load("test-123") is None
    persistence.save(state)
    assert persistence.load("test-123") is not None
    assert persistence.load("test-123").discussion_id == "test-123"
    assert persistence.exists("test-123")

    persistence.clear()
    assert persistence.load("test-123") is None


def test_agent_failure_continues_discussion():
    """Verify that if one agent fails, the discussion continues."""
    orchestrator = DiscussionOrchestrator()

    good_agent = MockAgent("GoodAgent")

    bad_agent = MagicMock()
    bad_agent.persona = MockPersona("BadAgent")
    bad_agent.respond.side_effect = RuntimeError("Agent crashed")
    bad_agent.generate_opinion.side_effect = RuntimeError("Agent crashed")

    result = orchestrator.start_discussion(
        topic="Failure test",
        agents=[good_agent, bad_agent],
        config=DiscussionConfig(num_rounds=2),
    )

    # Discussion should complete despite bad agent
    assert result.status == DiscussionStatus.COMPLETED
    assert result.rounds_completed == 2

    # Good agent messages should exist
    good_messages = [m for m in result.messages if m.agent_name == "GoodAgent"]
    assert len(good_messages) == 2

    # Bad agent should have error messages
    bad_messages = [m for m in result.messages if m.agent_name == "BadAgent"]
    assert len(bad_messages) == 2
    for m in bad_messages:
        assert "Agent error" in m.content


def test_retrieval_disabled():
    """Verify retrieval is skipped when enable_retrieval=False."""
    mock_retriever = MockRetriever()
    orchestrator = DiscussionOrchestrator(retriever=mock_retriever)
    agent = MockAgent("Agent1")

    result = orchestrator.start_discussion(
        topic="No retrieval test",
        agents=[agent],
        config=DiscussionConfig(num_rounds=2, enable_retrieval=False),
    )

    assert len(mock_retriever.retrieve_calls) == 0
    assert len(result.retrieval_events) == 0


def test_opinion_tracking_disabled():
    """Verify opinion tracking is skipped when enable_opinion_tracking=False."""
    orchestrator = DiscussionOrchestrator()
    agent = MockAgent("Agent1")

    result = orchestrator.start_discussion(
        topic="No opinion test",
        agents=[agent],
        config=DiscussionConfig(num_rounds=2, enable_opinion_tracking=False),
    )

    assert len(result.opinions) == 0
    assert len(agent.opinion_calls) == 0
