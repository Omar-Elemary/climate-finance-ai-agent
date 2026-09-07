#!/usr/bin/env python
"""
Week 3 Demo — Multi-Agent Discussion Orchestration

Demonstrates a real multi-round discussion between multiple climate finance
personas, managed by the DiscussionOrchestrator.

Usage:
    python week3_demo.py                          # uses mock agents (no LLM needed)
    python week3_demo.py --live                   # uses real Week 2 agents + LLM
    python week3_demo.py --rounds 5               # custom number of rounds
    python week3_demo.py --topic "Your topic"     # custom topic
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from src.orchestration import (
    DiscussionOrchestrator,
    DiscussionConfig,
    DiscussionResult,
    DiscussionStatus,
    InMemoryPersistence,
)


# ---------------------------------------------------------------------------
# Mock agents for demonstration without LLM
# ---------------------------------------------------------------------------

class DemoAgent:
    """Deterministic agent for demo without requiring an LLM provider."""

    def __init__(self, name: str, stance: str):
        self.name = name
        self.stance = stance
        self.persona = type("P", (), {"name": name})()
        self._turn = 0

    def respond(self, message: str) -> str:
        self._turn += 1
        return (
            f"[{self.name}] (Turn {self._turn}) "
            f"As a {self.stance}, I believe climate finance should be "
            f"allocated based on rigorous evidence and equitable frameworks. "
            f"From the discussion context, I observe that participants are "
            f"building on each other's arguments, which strengthens our "
            f"collective analysis."
        )

    def generate_opinion(self, topic: str) -> dict:
        return {
            "topic": topic,
            "persona": self.name,
            "opinion": f"{self.name} supports evidence-based climate finance allocation.",
            "evidence": ["Climate finance data point 1", "Evidence chunk 2"],
            "sources": ["https://example.com/climate-report"],
        }


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def print_header(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def print_round_header(round_num: int, total: int) -> None:
    print(f"\n{'─' * 70}")
    print(f"  ROUND {round_num}/{total}")
    print(f"{'─' * 70}")


def print_agent_message(agent_name: str, content: str) -> None:
    # Truncate for display
    display = content[:200] + "..." if len(content) > 200 else content
    print(f"  [{agent_name}]: {display}")


def print_opinion_evolution(opinions: dict) -> None:
    print_header("OPINION EVOLUTION")
    for agent_id, records in opinions.items():
        print(f"\n  {agent_id}:")
        for record in records:
            opinion_preview = record.opinion[:100] + "..." if len(record.opinion) > 100 else record.opinion
            print(f"    Round {record.round}: {opinion_preview}")


def print_retrieval_events(events: list) -> None:
    if not events:
        return
    print_header("RETRIEVAL EVENTS")
    for event in events:
        print(f"  Round {event.round} | Agent: {event.agent_id}")
        print(f"    Query: {event.query[:80]}...")
        print(f"    Results: {len(event.results)} chunks retrieved")


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

def run_mock_demo(topic: str, num_rounds: int) -> DiscussionResult:
    """Run demo with mock agents (no LLM required)."""
    print_header("WEEK 3 DEMO — MOCK AGENTS (No LLM Required)")

    # Create mock agents
    agents = [
        DemoAgent("Climate Investor", "financial analyst focused on ROI"),
        DemoAgent("Environmental Scientist", "researcher focused on ecological impact"),
        DemoAgent("Policy Expert", "government advisor focused on regulatory frameworks"),
    ]

    # Configure discussion
    config = DiscussionConfig(
        num_rounds=num_rounds,
        enable_retrieval=False,  # No retriever in mock mode
        enable_opinion_tracking=True,
    )

    # Create persistence to inspect state
    persistence = InMemoryPersistence()

    # Create and run orchestrator
    orchestrator = DiscussionOrchestrator(persistence=persistence)

    print(f"\nTopic: {topic}")
    print(f"Participants: {[a.name for a in agents]}")
    print(f"Rounds: {num_rounds}")

    result = orchestrator.start_discussion(
        topic=topic,
        agents=agents,
        config=config,
    )

    # Display results
    print_header("DISCUSSION MESSAGES")
    current_round = 0
    for msg in result.messages:
        if msg.round != current_round:
            current_round = msg.round
            print_round_header(current_round, result.rounds_completed)
        print_agent_message(msg.agent_name, msg.content)

    # Display opinion evolution
    print_opinion_evolution(result.opinions)

    # Display retrieval events
    print_retrieval_events(result.retrieval_events)

    # Summary
    print_header("DISCUSSION SUMMARY")
    print(f"  Discussion ID:  {result.discussion_id}")
    print(f"  Topic:          {result.topic}")
    print(f"  Participants:   {result.participants}")
    print(f"  Rounds:         {result.rounds_completed}")
    print(f"  Total Messages: {len(result.messages)}")
    print(f"  Status:         {result.status.value}")
    print(f"  Started:        {result.started_at.isoformat()}")
    print(f"  Completed:      {result.completed_at.isoformat() if result.completed_at else 'N/A'}")

    # Verify persistence
    persisted = persistence.load(result.discussion_id)
    print(f"  Persisted:      {'Yes' if persisted else 'No'}")

    return result


def run_live_demo(topic: str, num_rounds: int) -> DiscussionResult:
    """Run demo with real Week 2 agents and LLM provider."""
    print_header("WEEK 3 DEMO — LIVE AGENTS (Requires LLM Provider)")

    try:
        from src.agent import Agent
        from src.llm import get_provider
        from src.personas import load_persona, list_personas
        from src.tools import RetrievalTool
    except ImportError as e:
        print(f"Error importing Week 2 modules: {e}")
        print("Make sure Week 2 is properly set up.")
        sys.exit(1)

    # Load LLM
    try:
        llm = get_provider()
    except ValueError as e:
        print(f"LLM Provider Error: {e}")
        print("Set LLM_PROVIDER and LLM_API_KEY in your .env file.")
        sys.exit(1)

    print(f"LLM Provider: {llm.provider_name} / {llm.model}")

    # Create agents from personas
    persona_names = list_personas()
    if not persona_names:
        print("No personas found in personas/ directory.")
        sys.exit(1)

    # Use first 3 personas
    selected = persona_names[:3]
    tools = [RetrievalTool()]
    agents = []
    for name in selected:
        persona = load_persona(name)
        agents.append(Agent(persona=persona, llm=llm, tools=tools))

    # Configure discussion
    config = DiscussionConfig(
        num_rounds=num_rounds,
        enable_retrieval=True,
        enable_opinion_tracking=True,
    )

    # Create orchestrator with real retriever
    from src.tools.retrieval import RetrievalTool as RT

    class RetrieverAdapter:
        """Adapter around Week 1 RetrievalTool to match Retriever Protocol."""
        def __init__(self):
            self._tool = RT()

        def retrieve(self, query: str, top_k: int = 3, **kwargs):
            result = self._tool.run(query=query, final_k=top_k)
            return result.data if result.success else []

    persistence = InMemoryPersistence()
    orchestrator = DiscussionOrchestrator(
        retriever=RetrieverAdapter(),
        persistence=persistence,
    )

    print(f"\nTopic: {topic}")
    print(f"Participants: {selected}")
    print(f"Rounds: {num_rounds}")

    result = orchestrator.start_discussion(
        topic=topic,
        agents=agents,
        config=config,
    )

    # Display summary
    print_header("DISCUSSION SUMMARY")
    print(f"  Discussion ID:  {result.discussion_id}")
    print(f"  Topic:          {result.topic}")
    print(f"  Participants:   {result.participants}")
    print(f"  Rounds:         {result.rounds_completed}")
    print(f"  Total Messages: {len(result.messages)}")
    print(f"  Opinions:       {sum(len(v) for v in result.opinions.values())} records")
    print(f"  Retrievals:     {len(result.retrieval_events)} events")
    print(f"  Status:         {result.status.value}")

    # Show first message from each round
    print_header("MESSAGES BY ROUND")
    for round_num in range(1, result.rounds_completed + 1):
        print_round_header(round_num, result.rounds_completed)
        round_msgs = [m for m in result.messages if m.round == round_num]
        for msg in round_msgs:
            print_agent_message(msg.agent_name, msg.content[:300])

    print_opinion_evolution(result.opinions)
    print_retrieval_events(result.retrieval_events)

    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Week 3 Multi-Agent Discussion Demo")
    parser.add_argument("--live", action="store_true", help="Use real Week 2 agents + LLM")
    parser.add_argument("--rounds", type=int, default=3, help="Number of discussion rounds")
    parser.add_argument("--topic", default=None, help="Discussion topic")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    topic = args.topic or (
        "Should developed countries significantly increase "
        "climate adaptation finance for developing nations, "
        "and what mechanisms should govern this allocation?"
    )

    if args.live:
        result = run_live_demo(topic, args.rounds)
    else:
        result = run_mock_demo(topic, args.rounds)

    # Final status
    print(f"\nDemo complete. Status: {result.status.value}")
    return result


if __name__ == "__main__":
    main()
