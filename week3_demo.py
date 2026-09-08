"""
Week 3 Demo — Climate Finance Multi-Agent Discussion Simulation.
"""

from src.graph.topology import AgentGraph
from src.routing.graph_router import GraphRouter
from src.orchestration.models import DiscussionConfig, DiscussionStatus
from src.orchestration.orchestrator import DiscussionOrchestrator
from src.orchestration.persistence import InMemoryPersistence


class DemoAgent:
    """Lightweight persona agent for simulation."""

    def __init__(self, agent_id: str, name: str, role: str):
        self.id = agent_id
        self.name = name
        self.role = role

    def respond(self, context: str) -> str:
        return f"[{self.name} - {self.role}]: Evaluating transition pathways and capital structure."

    def generate_opinion(self, topic: str) -> dict:
        return {
            "opinion": f"{self.name} advocates for green taxonomy compliance across industries.",
            "evidence": ["EU Taxonomy Regulation 2020/852", "ISSB Disclosure Standards"],
            "sources": ["COP28 Net-Zero Synthesis"],
        }


def run_week3_demo():
    print("=" * 75)
    print("🌍 Week 3 Multi-Agent Discussion System: Climate Finance Simulation")
    print("=" * 75)

    agents = [
        DemoAgent("investor", "Institutional Investor", "Capital Allocation"),
        DemoAgent("policy_maker", "Regulatory Authority", "Climate Compliance"),
        DemoAgent("env_specialist", "ESG Analyst", "Environmental Impact"),
        DemoAgent("industry_cfo", "Industrial CFO", "Operational Transition"),
    ]
    agent_ids = [a.id for a in agents]
    print(f"\n[1] Initializing Agent Ecosystem: {agent_ids}")

    graph = AgentGraph.create_persona_based_topology(agent_ids)
    is_connected = graph.is_strongly_connected()
    print(f"    Graph strong connectivity verified: {is_connected}")
    assert is_connected, "Graph must be strongly connected!"

    print("\n[2] Setting up GraphRouter & In-Memory Persistence Layer...")
    router = GraphRouter(graph)
    persistence = InMemoryPersistence()

<<<<<<< HEAD
=======
    # 4. Orchestration Configuration
>>>>>>> 5e58aea056ce91918fb3deadf1b9475b5453483e
    config = DiscussionConfig(
        num_rounds=3,
        enable_retrieval=False,
        enable_opinion_tracking=True,
    )
    orchestrator = DiscussionOrchestrator(
        router=router,
        persistence=persistence,
    )

    topic = "Financing Industrial Decarbonization and Green Hydrogen"
    print(f"\n[3] Launching Discussion on: '{topic}' across 3 rounds...")

    result = orchestrator.start_discussion(
        topic=topic,
        agents=agents,
        config=config,
    )

    print(f"\n[4] Discussion Lifecycle Completed:")
    print(f"    - Discussion ID: {result.discussion_id}")
    print(f"    - Status: {result.status.value}")
    print(f"    - Rounds Completed: {result.rounds_completed}")
    print(f"    - Messages Exchanged: {len(result.messages)}")

<<<<<<< HEAD
=======
    # 7. Display Opinions Across Rounds
>>>>>>> 5e58aea056ce91918fb3deadf1b9475b5453483e
    print("\n[5] Recorded Opinions Trajectory:")
    for agent_id, history in result.opinions.items():
        for record in history:
            print(f"    - Round {record.round} | {record.agent_name}: \"{record.opinion[:60]}...\"")

    print("\n[6] Validating State Persistence Checkpoints:")
    loaded_state = persistence.load(result.discussion_id)
    if loaded_state and loaded_state.status == DiscussionStatus.COMPLETED:
        print(f"    State successfully saved and reconstructed for ID: {loaded_state.discussion_id}")
    else:
        raise RuntimeError("State persistence validation failed!")

    print("\n" + "=" * 75)
    print(" Week 3 Simulation Finished Successfully.")
    print("=" * 75)


if __name__ == "__main__":
    run_week3_demo()
    