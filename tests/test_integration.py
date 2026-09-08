"""
Integration Tests for Week 3 Multi-Agent Discussion Architecture.

Covers all 6 mandatory testing requirements:
1. Graph Test (Strong Connectivity)
2. Routing Test (Message flow adherence)
3. Multi-round Test (Execution of >= 3 rounds)
4. Retrieval Test (Accessing retrieval events during discussion)
5. Persistence Test (State saving and reconstruction)
6. Opinion Tracking Test (Recording opinions across rounds)
"""

from unittest.mock import MagicMock
import pytest

from src.orchestration.models import (
    DiscussionConfig,
    DiscussionState,
    DiscussionStatus,
    Message,
    OpinionRecord,
    RetrievalEvent,
)
from src.orchestration.orchestrator import DiscussionOrchestrator
from src.graph.topology import AgentGraph
from src.routing.graph_router import GraphRouter
from src.orchestration.persistence import InMemoryPersistence


class MockAgent:
    """Mock Agent conforming to the expected interface for integration testing."""

    def __init__(self, agent_id: str, name: str):
        self.id = agent_id
        self.name = name

    def respond(self, context: str) -> str:
        return f"{self.name} perspective based on discussion."

    def generate_opinion(self, topic: str) -> dict:
        return {
            "opinion": f"{self.name} supports balanced climate funding.",
            "evidence": ["Screening criteria taxonomy doc"],
            "sources": ["COP28 Synthesis Report"],
        }


# ==============================================================================
# 1. Graph test: Verify configured discussion graph is strongly connected
# ==============================================================================
def test_graph_strongly_connected():
    agents = ["investor", "policy_maker", "env_specialist", "industry_cfo"]

    ring_graph = AgentGraph.create_ring_topology(agents)
    assert ring_graph.is_strongly_connected() is True

    persona_graph = AgentGraph.create_persona_based_topology(agents)
    assert persona_graph.is_strongly_connected() is True

    broken_graph = AgentGraph(["a", "b", "c"])
    broken_graph.add_edge("a", "b")
    assert broken_graph.is_strongly_connected() is False


# ==============================================================================
# 2. Routing test: Verify messages are delivered according to graph relationships
# ==============================================================================
def test_routing_delivers_according_to_graph():
    agents = ["investor", "policy_maker", "env_specialist"]
    graph = AgentGraph.create_ring_topology(agents)
    router = GraphRouter(graph)

    recipients = router.get_next_recipients("investor")
    assert recipients == ["policy_maker"]

    broken_graph = AgentGraph(["a", "b"])
    broken_graph.add_edge("a", "b")
    with pytest.raises(ValueError, match="strongly connected"):
        GraphRouter(broken_graph)


# ==============================================================================
# 3. Multi-round test: Verify system executes at least three rounds
# ==============================================================================
def test_multi_round_execution():
    agents = [
        MockAgent("investor", "Investor"),
        MockAgent("policy_maker", "Policy Maker"),
        MockAgent("env_specialist", "Environmental Specialist"),
    ]
    agent_ids = [a.id for a in agents]
    graph = AgentGraph.create_persona_based_topology(agent_ids)
    router = GraphRouter(graph)
    persistence = InMemoryPersistence()

    config = DiscussionConfig(num_rounds=3)
    orchestrator = DiscussionOrchestrator(
        router=router,
        persistence=persistence,
    )

    result = orchestrator.start_discussion(
        topic="Financing Green Hydrogen Infrastructure",
        agents=agents,
        config=config,
    )

    assert result.rounds_completed >= 3
    assert result.status == DiscussionStatus.COMPLETED
    assert len(result.messages) > 0


# ==============================================================================
# 4. Retrieval test: Verify agent accesses retrieval system during discussion
# ==============================================================================
def test_agent_retrieval_during_discussion():
    agents = [
        MockAgent("investor", "Investor"),
        MockAgent("policy_maker", "Policy Maker"),
    ]
    agent_ids = [a.id for a in agents]
    graph = AgentGraph.create_ring_topology(agent_ids)
    router = GraphRouter(graph)

    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = [
        {"title": "EU Taxonomy Report", "snippet": "Technical screening criteria"}
    ]

    config = DiscussionConfig(num_rounds=1, enable_retrieval=True)
    orchestrator = DiscussionOrchestrator(
        router=router,
        retriever=mock_retriever,
    )

    result = orchestrator.start_discussion(
        topic="EU Green Taxonomy Guidelines",
        agents=agents,
        config=config,
    )

    assert len(result.retrieval_events) > 0
    event = result.retrieval_events[0]
    assert isinstance(event, RetrievalEvent)
    assert event.query != ""
    assert len(event.results) > 0


# ==============================================================================
# 5. Persistence test: Verify discussion is saved and reconstructed
# ==============================================================================
def test_discussion_persistence_save_and_reconstruct():
    persistence = InMemoryPersistence()
    disc_id = "test-disc-2026"

    state = DiscussionState(
        discussion_id=disc_id,
        topic="Carbon Border Adjustment Mechanism",
        participants=["investor", "industry_cfo"],
        total_rounds=3,
        current_round=3,
        status=DiscussionStatus.COMPLETED,
    )

    msg = Message(
        message_id="msg-001",
        discussion_id=disc_id,
        round=1,
        agent_id="industry_cfo",
        agent_name="Industry CFO",
        content="CBAM will increase compliance costs.",
    )
    state.add_message(msg)

    persistence.save(state)
    assert persistence.exists(disc_id) is True

    loaded_state = persistence.load(disc_id)
    assert loaded_state is not None
    assert loaded_state.discussion_id == disc_id
    assert loaded_state.topic == "Carbon Border Adjustment Mechanism"
    assert loaded_state.status == DiscussionStatus.COMPLETED
    assert len(loaded_state.messages) == 1
    assert loaded_state.messages[0].content == msg.content


# ==============================================================================
# 6. Opinion tracking test: Verify opinion states are recorded across rounds
# ==============================================================================
def test_opinion_tracking_across_rounds():
    state = DiscussionState(
        discussion_id="disc-opinions",
        topic="Voluntary Carbon Markets",
        participants=["investor"],
        total_rounds=3,
    )

    for r in range(1, 4):
        state.add_opinion(
            OpinionRecord(
                agent_id="investor",
                agent_name="Climate Investor",
                round=r,
                opinion=f"Investor sentiment at round {r}",
                evidence=[f"Evidence citation {r}"],
            )
        )

    history = state.get_opinion_history("investor")
    assert len(history) == 3
    assert [op.round for op in history] == [1, 2, 3]
    assert history[0].opinion == "Investor sentiment at round 1"
    assert history[2].opinion == "Investor sentiment at round 3"
    