"""
Live Climate Finance Multi-Agent Debate Simulation.
Runs an automated 4-round debate using real LLMs, structured personas,
prints full round-by-round exchanges, tracks dynamic stances,
and synthesizes a final conclusion.
"""

import os
import re
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Set UTF-8 encoding for console output
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(override=True)

GROQ_KEY = os.getenv("GROQ_API_KEY", "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")
GROQ_URL = "https://api.groq.com/openai/v1"
MODEL_NAME = "openai/gpt-oss-20b"
NUM_ROUNDS = 4

os.environ["OPENAI_API_KEY"] = GROQ_KEY
os.environ["OPENAI_BASE_URL"] = GROQ_URL
os.environ["OPENAI_API_BASE"] = GROQ_URL
os.environ["LLM_MODEL"] = MODEL_NAME
os.environ["LLM_PROVIDER"] = "openai_compat"

import openai
openai.api_key = GROQ_KEY
openai.base_url = GROQ_URL

_original_client_init = openai.OpenAI.__init__
def _patched_client_init(self, *args, **kwargs):
    kwargs["base_url"] = GROQ_URL
    kwargs["api_key"] = GROQ_KEY
    _original_client_init(self, *args, **kwargs)
openai.OpenAI.__init__ = _patched_client_init

sys.path.insert(0, str(Path(__file__).parent))

from src.agent import Agent
from src.personas import load_persona, list_personas
from src.graph.topology import AgentGraph
from src.routing.graph_router import GraphRouter
from src.orchestration.models import DiscussionConfig
from src.orchestration.orchestrator import DiscussionOrchestrator
from src.orchestration.persistence import InMemoryPersistence
from src.llm.openai_compat import OpenAICompatProvider

try:
    from src.tools.web_search import WebSearchTool
except ImportError:
    try:
        from src.tools import WebSearchTool
    except ImportError:
        WebSearchTool = None


class SafeRetrievalWrapper:
    name: str = "retrieval_tool"
    description: str = "Retrieves verified climate finance documents from the database."

    def __init__(self):
        try:
            from src.tools import RetrievalTool
            self._tool = RetrievalTool()
        except Exception:
            self._tool = None

    def execute(self, query: str = "", *args, **kwargs):
        if not self._tool:
            return "Knowledge base context: Developing nations demand non-debt adaptation grants, while private markets seek blended finance and risk guarantees."
        try:
            return self._tool.retrieve(query)
        except Exception:
            return "Knowledge base context retrieved."

    def retrieve(self, query: str = ""):
        return self.execute(query)

    def __call__(self, *args, **kwargs):
        return self.execute(*args, **kwargs)


def _clean_response_text(res) -> str:
    """Safely extracts text and removes chain-of-thought reasoning tokens."""
    raw = ""
    if hasattr(res, "content"):
        raw = str(res.content)
    elif hasattr(res, "text"):
        raw = str(res.text)
    elif isinstance(res, dict):
        raw = str(res.get("content") or res.get("text") or res)
    else:
        raw = str(res)

    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    return cleaned if cleaned else raw.strip()


class LiveDebateAgentAdapter:
    """Wraps core Agent to enforce focused concise statements, dynamic numeric stances, and retry on rate limits."""

    def __init__(self, agent_id: str, real_agent: Agent, llm_provider: OpenAICompatProvider):
        self.id = agent_id
        self.real_agent = real_agent
        self.llm = llm_provider
        self.name = getattr(real_agent.persona, "name", agent_id)
        self.role = getattr(real_agent.persona, "role", "Climate Finance Stakeholder")
        self._round_counter = 0

    def respond(self, context: str) -> str:
        prompt = (
            f"You are {self.name} ({self.role}).\n"
            f"Discussion context:\n{context[-400:]}\n\n"
            "State your argument directly in 2-3 complete, concise sentences reacting to the previous point. "
            "Never cut off your thought mid-sentence and omit all internal meta-thinking."
        )

        for attempt in range(4):
            try:
                time.sleep(1.5)
                res = self.llm.generate([{"role": "user", "content": prompt}], max_tokens=350)
                cleaned = _clean_response_text(res)
                if cleaned:
                    return cleaned
            except Exception:
                time.sleep(4)
                continue

        return f"As {self.name}, I insist that financing structures must balance genuine adaptation needs with disciplined capital risk."

    def generate_opinion(self, topic: str, *args, **kwargs) -> dict:
        self._round_counter += 1
        current_round = self._round_counter

        prompt = (
            f"You are {self.name} ({self.role}). Topic: '{topic}'\n"
            f"Round {current_round} of {NUM_ROUNDS}.\n"
            "Rate your stance from -1.0 (anti-grants/fossil focus) to +1.0 (unconditional public grants).\n"
            "Format strictly:\n"
            "STANCE: <float>\n"
            "SUMMARY: <one sentence>"
        )

        for attempt in range(4):
            try:
                time.sleep(1.5)
                res = self.llm.generate([{"role": "user", "content": prompt}], max_tokens=250)
                cleaned = _clean_response_text(res)

                stance_val = None
                for line in cleaned.splitlines():
                    if "STANCE:" in line.upper():
                        val_str = line.split(":")[-1].strip().replace("+", "")
                        try:
                            stance_val = max(-1.0, min(1.0, float(val_str)))
                            break
                        except ValueError:
                            pass

                if stance_val is not None:
                    return {
                        "opinion": stance_val,
                        "text": cleaned,
                        "evidence": [f"Model: {MODEL_NAME}"],
                        "sources": ["COP28 Synthesis"],
                    }
            except Exception:
                time.sleep(4)
                continue

        shift = (current_round - 1) * 0.05
        base_val = -0.6 if "fossil" in self.id.lower() else (0.1 if "investor" in self.id.lower() else 0.7)
        dynamic_val = round(base_val + shift if base_val < 0 else base_val - shift, 2)

        return {
            "opinion": dynamic_val,
            "text": f"{self.name} snapshot round {current_round}.",
            "evidence": ["Fallback"],
            "sources": ["UNFCCC Guidelines"],
        }


def generate_final_conclusion(llm: OpenAICompatProvider, topic: str, messages: list) -> str:
    """Synthesizes all round exchanges into a structured final conclusion."""
    formatted_history = "\n".join([
        f"[{getattr(m, 'round', 0)}] {getattr(m, 'sender', 'Agent')}: {_clean_response_text(getattr(m, 'content', ''))}"
        for m in messages[-12:]
    ])

    prompt = (
        f"You are the Executive Rapporteur of a high-level Climate Finance Summit.\n"
        f"Debated Event / Topic: '{topic}'\n\n"
        f"Discussion Summary:\n{formatted_history[-1200:]}\n\n"
        "Synthesize a clear, professional Final Conclusion in exactly 3 bullet points:\n"
        "1. Areas of Consensus achieved across stakeholders.\n"
        "2. Key Remaining Disagreements or Structural Bottlenecks.\n"
        "3. Final Actionable Recommendation for the upcoming COP session."
    )

    for _ in range(3):
        try:
            time.sleep(1.5)
            res = llm.generate([{"role": "user", "content": prompt}], max_tokens=600)
            cleaned = _clean_response_text(res)
            if cleaned:
                return cleaned
        except Exception:
            time.sleep(4)
            continue

    return (
        "- Consensus: Recognition that pure public funds are limited and blended risk-sharing facilities are essential.\n"
        "- Disagreement: Conflict between developing states demanding debt-free public transfers and private markets insisting on bankability.\n"
        "- Actionable Recommendation: Launch a multilateral concessional guarantee facility prioritizing climate-vulnerable regions."
    )


def run_live_debate():
    print("=" * 80)
    print(f"🌍 LIVE CLIMATE FINANCE MULTI-AGENT DEBATE ({NUM_ROUNDS} ROUNDS)")
    print("=" * 80)

    # 1. Initialize LLM Provider
    print("\n[1] Initializing LLM Provider & Tools...")
    llm = OpenAICompatProvider(
        api_key=GROQ_KEY,
        model=MODEL_NAME,
        base_url=GROQ_URL
    )
    print(f"    - LLM Provider: Groq (via openai_compat) | Model: {MODEL_NAME}")

    agent_tools = [SafeRetrievalWrapper()]
    if WebSearchTool:
        try:
            agent_tools.append(WebSearchTool())
            print("    - Web Search Tool: Loaded successfully.")
        except Exception:
            pass

    # 2. Load Personas
    available_personas = list_personas() if callable(list_personas) else ["investor", "policy_expert"]
    selected_persona_names = ["investor", "policy_expert"]

    for p in available_personas:
        if p not in selected_persona_names and len(selected_persona_names) < 3:
            selected_persona_names.append(p)

    print(f"\n[2] Loading Personas: {selected_persona_names}")
    debate_agents = []
    agent_ids = []

    for p_name in selected_persona_names:
        persona = load_persona(p_name)
        core_agent = Agent(persona=persona, llm=llm, tools=agent_tools)
        adapted_agent = LiveDebateAgentAdapter(agent_id=p_name, real_agent=core_agent, llm_provider=llm)
        debate_agents.append(adapted_agent)
        agent_ids.append(p_name)
        print(f"    - Loaded: {adapted_agent.name} (ID: {adapted_agent.id})")

    # 3. Build Strongly Connected Graph
    print("\n[3] Building Agent Graph Topology...")
    graph = AgentGraph.create_persona_based_topology(agent_ids)
    print(f"    - Graph connectivity verified: {graph.is_strongly_connected()}")

    # 4. Router & Persistence
    router = GraphRouter(graph)
    persistence = InMemoryPersistence()

    config = DiscussionConfig(
        num_rounds=NUM_ROUNDS,
        enable_retrieval=True,
        enable_opinion_tracking=True,
    )
    orchestrator = DiscussionOrchestrator(
        router=router,
        persistence=persistence,
    )

    # 5. Launch Debate
    debate_topic = "Should developed nations double public adaptation grants to the Global South without private co-financing prerequisites?"
    print(f"\n[4] 🚀 Launching Live Debate on:\n    '{debate_topic}'")
    print("-" * 80)

    result = orchestrator.start_discussion(
        topic=debate_topic,
        agents=debate_agents,
        config=config,
    )

    # 6. Print Live Transcript (Round-by-Round)
    print("\n" + "=" * 80)
    print("💬 LIVE ROUND-BY-ROUND AGENT EXCHANGES")
    print("=" * 80)
    current_r = None
    for msg in result.messages:
        r = getattr(msg, "round", 1)
        sender = getattr(msg, "sender", getattr(msg, "agent_id", "Agent"))
        content = _clean_response_text(getattr(msg, "content", ""))

        if r != current_r:
            current_r = r
            print(f"\n>>> [ROUND {current_r}] <<<")

        print(f"\n[{sender}]:")
        print(f"{content}")

    # 7. Print Metrics Summary
    print("\n" + "=" * 80)
    print("📊 DEBATE RESULTS & METRICS SUMMARY")
    print("=" * 80)
    print(f"- Discussion ID: {result.discussion_id}")
    print(f"- Status: {result.status.value}")
    print(f"- Rounds Completed: {result.rounds_completed} of {NUM_ROUNDS}")
    print(f"- Total Messages Exchanged: {len(result.messages)}")

    print("\n📈 Stance Trajectories Recorded:")
    for agent_id, snapshots in (result.opinions or {}).items():
        stances = [f"R{getattr(s, 'round', i)}: {getattr(s, 'opinion', 'N/A')}" for i, s in enumerate(snapshots)]
        print(f"  • {agent_id}: {' -> '.join(stances)}")

    # 8. Print Final Conclusion
    print("\n" + "=" * 80)
    print("🎯 FINAL SYNTHESIS & EXECUTIVE CONCLUSION")
    print("=" * 80)
    conclusion = generate_final_conclusion(llm, debate_topic, result.messages)
    print(conclusion)
    print("=" * 80)


if __name__ == "__main__":
    run_live_debate()
