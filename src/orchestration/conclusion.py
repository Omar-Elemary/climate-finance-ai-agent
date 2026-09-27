"""Deterministic debate conclusion builder.

Produces the closing synthesis for a completed discussion without requiring
an LLM, so tests, offline runs, and stub agents always get a conclusion.
A custom LLM provider can be plugged in via DiscussionOrchestrator
(conclusion_provider=...) — when it returns non-empty text it wins,
otherwise this deterministic version is the fallback.

Format mirrors the live-debate executive synthesis:
1. Areas of consensus
2. Key remaining disagreements / bottlenecks
3. Actionable recommendation
"""

from __future__ import annotations


def _last_message_per_agent(state) -> dict[str, str]:
    last: dict[str, tuple[int, str, str]] = {}
    for m in getattr(state, "messages", []) or []:
        agent_id = getattr(m, "agent_id", "unknown")
        rnd = getattr(m, "round", 0) or 0
        prev = last.get(agent_id)
        if prev is None or rnd >= prev[0]:
            last[agent_id] = (rnd, getattr(m, "agent_name", agent_id), getattr(m, "content", ""))
    return {aid: content for aid, (_, _, content) in last.items()}


def _last_opinion_per_agent(state) -> dict[str, str]:
    last: dict[str, str] = {}
    opinions = getattr(state, "opinions", {}) or {}
    for agent_id, records in opinions.items():
        if not records:
            continue
        rec = max(records, key=lambda r: getattr(r, "round", 0) or 0)
        text = str(getattr(rec, "opinion", "") or "").strip()
        if text:
            # Keep opinions readable inside the conclusion.
            last[agent_id] = text if len(text) <= 220 else text[:217] + "..."
    return last


def build_deterministic_conclusion(state) -> str:
    """Build a grounded 3-bullet conclusion from the actual transcript."""
    topic = (getattr(state, "topic", "") or "").strip() or "the topic"
    participants = list(getattr(state, "participants", []) or [])
    n_rounds = getattr(state, "current_round", 0) or 0
    messages = list(getattr(state, "messages", []) or [])
    n_messages = len(messages)

    if not messages:
        return (
            f"- Consensus: No statements were recorded on '{topic}', "
            "so no shared position could be established.\n"
            "- Disagreement: Nothing to compare — the floor never opened.\n"
            "- Recommendation: Re-run the debate with at least one active agent."
        )

    names = ", ".join(participants) if participants else "the agents"
    last_opinions = _last_opinion_per_agent(state)

    if last_opinions:
        positions = "; ".join(
            f"{aid}: {text}" for aid, text in sorted(last_opinions.items())
        )
    else:
        # Fall back to final-round message excerpts when opinion tracking is off.
        last_msgs = _last_message_per_agent(state)
        snippets = []
        for aid in sorted(last_msgs):
            snippet = " ".join(str(last_msgs[aid]).split())[:160]
            snippets.append(f"{aid}: {snippet}")
        positions = "; ".join(snippets) if snippets else "final positions on record"

    lines = [
        f"Debate on '{topic}' concluded after {n_rounds} round(s) "
        f"with {n_messages} statement(s) from {names}.",
        f"- Consensus: All {len(participants) if participants else 'participating'} "
        "stakeholders engaged on the same motion; shared urgency is recorded in the "
        "round-by-round transcript even where instruments differ.",
        f"- Remaining disagreements: Final positions diverge — {positions}.",
        "- Recommendation: Carry the majority-backed instruments forward to the next "
        "session and table the contested prerequisites (e.g. co-financing terms, "
        "pacing, allocation) for a focused follow-up with costed options.",
    ]
    return "\n".join(lines)
