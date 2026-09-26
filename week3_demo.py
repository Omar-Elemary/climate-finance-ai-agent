"""
Week 3 Demo — Climate Finance Multi-Agent Discussion Simulation.
"""

import re
import sys

# Windows consoles default to cp1252, which cannot print emoji (🌍).
# week2_demo.py already does this; mirror it here so `python week3_demo.py`
# works in PowerShell/cmd without UnicodeEncodeError.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.graph.topology import AgentGraph
from src.routing.graph_router import GraphRouter
from src.orchestration.models import DiscussionConfig, DiscussionStatus
from src.orchestration.orchestrator import DiscussionOrchestrator
from src.orchestration.persistence import InMemoryPersistence


# Role-specific opinion arcs: each agent's position EVOLVES per round
# (Round 1: initial stance -> Round 2: react to others -> Round 3: refined deal).
# This fixes Hanaa's remark that every round printed the identical
# "advocates for green taxonomy compliance" placeholder.
OPINION_ARCS = {
    "investor": [
        {
            "opinion": (
                "Green hydrogen needs bankability first: predictable returns, "
                "de-risked cash flows, and blended finance to crowd in private capital."
            ),
            "evidence": ["IRENA hydrogen cost outlook", "Blended finance deal tracker"],
            "sources": ["IRENA Green Hydrogen Outlook"],
        },
        {
            "opinion": (
                "The CFO's CAPEX concern is valid — first-loss tranches plus "
                "power-price hedges would unlock our ticket; we can accept lower "
                "yields if downside is capped."
            ),
            "evidence": ["First-loss facility term sheets", "CfD price-hedge precedents"],
            "sources": ["COP28 Net-Zero Synthesis"],
        },
        {
            "opinion": (
                "Conditional yes: public guarantees are acceptable only if EU taxonomy "
                "thresholds and independent MRV stay binding, with sunset clauses "
                "as costs decline."
            ),
            "evidence": ["EU Taxonomy Regulation 2020/852", "Sunset-clause guarantee designs"],
            "sources": ["EU Taxonomy Compass"],
        },
    ],
    "policy_maker": [
        {
            "opinion": (
                "Taxonomy alignment and a credible transition plan must gate any "
                "support: no compliance, no public money."
            ),
            "evidence": ["EU Taxonomy Regulation 2020/852", "ISSB Disclosure Standards"],
            "sources": ["COP28 Net-Zero Synthesis"],
        },
        {
            "opinion": (
                "Guarantees can coexist with compliance if additionality thresholds "
                "are enforced — the ESG analyst's verification demand should be "
                "written into the instrument, not added later."
            ),
            "evidence": ["Additionality criteria drafts", "State-aid compliance notes"],
            "sources": ["UNFCCC NDC guidance"],
        },
        {
            "opinion": (
                "Final position: phase guarantees with sunset clauses tied to "
                "electrolyser cost declines, keeping emissions thresholds enforceable "
                "throughout."
            ),
            "evidence": ["Phased subsidy precedents", "MRV enforcement cases"],
            "sources": ["IEA Hydrogen Review"],
        },
    ],
    "env_specialist": [
        {
            "opinion": (
                "Lifecycle emissions and additionality must be verified before a "
                "single euro flows — grid-powered electrolysis can be worse than "
                "grey hydrogen."
            ),
            "evidence": ["Hydrogen lifecycle assessments", "Additionality studies"],
            "sources": ["IPCC AR6 WG3"],
        },
        {
            "opinion": (
                "Warning: the guarantees discussed must not subsidise non-additional "
                "projects. Ring-fence support to new renewable capacity with "
                "hourly matching."
            ),
            "evidence": ["Hourly-matching pilots", "Greenwashing enforcement actions"],
            "sources": ["WRI hydrogen safeguards"],
        },
        {
            "opinion": (
                "Support conditional finance only with independent MRV and public "
                "disclosure — that reconciles the investor's bankability need with "
                "environmental integrity."
            ),
            "evidence": ["Independent MRV frameworks", "Disclosure best practice"],
            "sources": ["ISSB Disclosure Standards"],
        },
    ],
    "industry_cfo": [
        {
            "opinion": (
                "CAPEX intensity and electricity opex make green hydrogen unbankable "
                "at current spreads — no board will approve FID on merchant risk alone."
            ),
            "evidence": ["Electrolyser CAPEX benchmarks", "Power-price forward curves"],
            "sources": ["IEA Hydrogen Review"],
        },
        {
            "opinion": (
                "With blended finance plus contracts-for-difference on the power price, "
                "FID becomes feasible — the investor's first-loss proposal directly "
                "answers our balance-sheet constraint."
            ),
            "evidence": ["CfD strike-price models", "FID case studies"],
            "sources": ["IRENA Green Hydrogen Outlook"],
        },
        {
            "opinion": (
                "Operational plan: phased electrolyser scale-up contingent on firm "
                "offtake contracts and verified emissions thresholds — financeable "
                "and deliverable."
            ),
            "evidence": ["Phased build-out plans", "Bankable offtake templates"],
            "sources": ["Industry offtake survey"],
        },
    ],
}

GENERIC_ARC = [
    {"opinion": "Opening position: presenting initial assessment of the topic.",
     "evidence": [], "sources": []},
    {"opinion": "Revised position: incorporating other participants' arguments.",
     "evidence": [], "sources": []},
    {"opinion": "Final position: converging on conditional agreement.",
     "evidence": [], "sources": []},
]


class DemoAgent:
    """Round-aware persona agent for simulation.

    - respond(context): parses CURRENT ROUND + DISCUSSION HISTORY out of the
      orchestrator-built context, so Round 2+ visibly reacts to peers.
    - generate_opinion(topic): advances one step along the agent's opinion
      arc per call (the orchestrator calls it once per round), so the
      recorded trajectory evolves instead of repeating a placeholder.
    """

    def __init__(self, agent_id: str, name: str, role: str):
        self.id = agent_id
        self.name = name
        self.role = role
        self._opinion_calls = 0

    def _arc(self) -> list:
        return OPINION_ARCS.get(self.id, GENERIC_ARC)

    @staticmethod
    def _parse_round(context: str) -> int:
        m = re.search(r"CURRENT ROUND:\s*(\d+)", context)
        return int(m.group(1)) if m else 1

    @staticmethod
    def _prior_speakers(context: str, own_name: str) -> list:
        speakers = []
        for m in re.finditer(r"\[(.+?)\]\s*\(Round \d+\):", context):
            name = m.group(1).strip()
            if name != own_name and name not in speakers:
                speakers.append(name)
        return speakers

    def respond(self, context: str) -> str:
        round_num = self._parse_round(context)
        stance = self._arc()[min(round_num, len(self._arc())) - 1]["opinion"]
        if round_num <= 1:
            return f"[{self.name} - {self.role}] Round 1 position: {stance}"
        others = self._prior_speakers(context, self.name)
        if others:
            return (
                f"[{self.name} - {self.role}] Round {round_num}, building on "
                f"{others[-1]}'s point: {stance}"
            )
        return f"[{self.name} - {self.role}] Round {round_num} update: {stance}"

    def generate_opinion(self, topic: str) -> dict:
        self._opinion_calls += 1
        idx = min(self._opinion_calls, len(self._arc())) - 1
        entry = self._arc()[idx]
        return {
            "opinion": f"Round {self._opinion_calls} | {entry['opinion']}",
            "evidence": list(entry.get("evidence", [])),
            "sources": list(entry.get("sources", [])),
        }


def run_week3_demo():
    print("=" * 75)
    print("🌍 Week 3 Multi-Agent Discussion System: Climate Finance Simulation")
    print("=" * 75)

    # 1. Initialize Persona Agents
    agents = [
        DemoAgent("investor", "Institutional Investor", "Capital Allocation"),
        DemoAgent("policy_maker", "Regulatory Authority", "Climate Compliance"),
        DemoAgent("env_specialist", "ESG Analyst", "Environmental Impact"),
        DemoAgent("industry_cfo", "Industrial CFO", "Operational Transition"),
    ]
    agent_ids = [a.id for a in agents]
    print(f"\n[1] Initializing Agent Ecosystem: {agent_ids}")

    # 2. Setup Strongly Connected Topology
    graph = AgentGraph.create_persona_based_topology(agent_ids)
    is_connected = graph.is_strongly_connected()
    print(f"    Graph strong connectivity verified: {is_connected}")
    assert is_connected, "Graph must be strongly connected!"

    # 3. Setup Router & Persistence
    print("\n[2] Setting up GraphRouter & In-Memory Persistence Layer...")
    router = GraphRouter(graph)
    persistence = InMemoryPersistence()

    # 4. Orchestration Configuration
    config = DiscussionConfig(
        num_rounds=3,
        enable_retrieval=False,
        enable_opinion_tracking=True,
    )
    orchestrator = DiscussionOrchestrator(
        router=router,
        persistence=persistence,
    )

    # 5. Execute Multi-Round Discussion
    topic = "Financing Industrial Decarbonization and Green Hydrogen"
    print(f"\n[3] Launching Discussion on: '{topic}' across 3 rounds...")

    result = orchestrator.start_discussion(
        topic=topic,
        agents=agents,
        config=config,
    )

    # 6. Verify Execution Metrics
    print(f"\n[4] Discussion Lifecycle Completed:")
    print(f"    - Discussion ID: {result.discussion_id}")
    print(f"    - Status: {result.status.value}")
    print(f"    - Rounds Completed: {result.rounds_completed}")
    print(f"    - Messages Exchanged: {len(result.messages)}")
    print(f"    - Graph edges (routing paths): {graph.to_dict()['edges']}")
    if result.messages:
        print(f"    - Sample routed message metadata: {result.messages[0].metadata}")

    # 7. Display Opinions Across Rounds (full text: proves round-aware evolution)
    print("\n[5] Recorded Opinions Trajectory (dynamic per round):")
    for agent_id, history in result.opinions.items():
        for record in history:
            print(f"    - Round {record.round} | {record.agent_name}: {record.opinion}")
        print()

    # 8. Persistence Verification
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
    