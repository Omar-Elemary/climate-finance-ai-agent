"""Core request/result contracts — thin wrappers, no duplication.

Request: ``DiscussionRequest`` carries exactly what the backend sends
(topic/domain/num_rounds/personas/enable_retrieval) and converts to the
EXISTING shared ``src.orchestration.DiscussionConfig`` via ``to_config()``.
No competing config model is introduced.

Result: the stable result IS the existing ``DiscussionState`` /
``DiscussionResult`` from ``src.orchestration.models`` (re-exported here).
Backend expectations are met because those models already expose
``.to_dict()`` with {discussion_id, topic, participants, messages[],
opinions{}, retrieval_events[], status, current_round, total_rounds,
started_at, completed_at, error}. Adapters below only *read* that shape
(agents/rounds/messages/retrieval_context views) — they never invent fields.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Reuse the shared Week 3 models — the single source of truth.
from src.orchestration.models import (  # noqa: F401  (public re-export)
    DiscussionConfig,
    DiscussionResult,
    DiscussionState,
    DiscussionStatus,
    Message,
    OpinionRecord,
    RetrievalEvent,
)

# Core-owned defaults mirror the backend contract (duplicated, not imported,
# so agent_core never depends on backend/).
DEFAULT_PERSONAS: list[str] = ["investor", "policy_expert", "scientist"]
MAX_ROUNDS = 10


@dataclass
class DiscussionRequest:
    """What the backend sends; what the Core executes.

    Attributes:
        topic: non-empty discussion topic (required).
        domain: optional API-level grouping tag. Accepted and echoed by the
            backend sidecar only — Week 3 state has no domain field, so the
            Core ignores it during execution (never persisted, never faked).
        num_rounds: 1..MAX_ROUNDS (backend already clamps 1..10).
        personas: persona names from personas/*.json; None -> DEFAULT_PERSONAS.
        enable_retrieval: forwarded to DiscussionConfig. Agents always carry
            the Week 1 RetrievalTool; this flag controls orchestrator-level
            retrieval context (off by default in week3_demo.py usage).
    """

    topic: str
    domain: str | None = None
    num_rounds: int = 3
    personas: list[str] | None = None
    enable_retrieval: bool = True

    def validated(self) -> "DiscussionRequest":
        """Return a normalized copy or raise InvalidDiscussionRequest."""
        from agent_core.exceptions import InvalidDiscussionRequest

        topic = (self.topic or "").strip()
        if not topic:
            raise InvalidDiscussionRequest("Topic must be a non-empty string.")
        if (
            not isinstance(self.num_rounds, int)
            or isinstance(self.num_rounds, bool)
            or not 1 <= self.num_rounds <= MAX_ROUNDS
        ):
            raise InvalidDiscussionRequest(
                f"num_rounds must be an integer between 1 and {MAX_ROUNDS}."
            )
        personas = list(self.personas) if self.personas is not None else list(
            DEFAULT_PERSONAS
        )
        if not personas:
            raise InvalidDiscussionRequest("At least one persona is required.")
        if len(set(personas)) != len(personas):
            raise InvalidDiscussionRequest("Duplicate persona names are not allowed.")
        return DiscussionRequest(
            topic=topic,
            domain=self.domain,
            num_rounds=self.num_rounds,
            personas=personas,
            enable_retrieval=bool(self.enable_retrieval),
        )

    def to_config(self) -> DiscussionConfig:
        """Translate into the existing Week 3 orchestration format."""
        req = self.validated()
        return DiscussionConfig(
            num_rounds=req.num_rounds,
            enable_retrieval=req.enable_retrieval,
            enable_opinion_tracking=True,
        )


# ---------------------------------------------------------------------------
# Read-only result views — derived from DiscussionState.to_dict(), the exact
# shape the backend consumes. Missing data is represented honestly (None/[]),
# never manufactured.
# ---------------------------------------------------------------------------

def _state_dict(state: DiscussionState | DiscussionResult | dict) -> dict:
    if isinstance(state, dict):
        return state
    to_dict = getattr(state, "to_dict", None)
    if callable(to_dict):
        result = to_dict()
        if isinstance(result, dict):
            return result
    raise TypeError(f"Cannot adapt {type(state).__name__} to result dict")


def agents_view(state: DiscussionState | DiscussionResult | dict) -> list[dict]:
    """ [{agent_id, agent_name}] from participants + opinion/message authors."""
    d = _state_dict(state)
    seen: dict[str, str] = {}
    for pid in d.get("participants", []) or []:
        seen.setdefault(str(pid), str(pid))
    for records in (d.get("opinions", {}) or {}).values():
        for rec in records or []:
            if isinstance(rec, dict) and rec.get("agent_id"):
                seen.setdefault(
                    str(rec["agent_id"]),
                    str(rec.get("agent_name", rec["agent_id"])),
                )
    for msg in d.get("messages", []) or []:
        if isinstance(msg, dict) and msg.get("agent_id"):
            seen.setdefault(
                str(msg["agent_id"]), str(msg.get("agent_name", msg["agent_id"]))
            )
    return [{"agent_id": aid, "agent_name": name} for aid, name in sorted(seen.items())]


def rounds_view(state: DiscussionState | DiscussionResult | dict) -> list[dict]:
    """ [{round, messages:[...]}] grouped by round number, sorted."""
    d = _state_dict(state)
    by_round: dict[int, list[dict]] = {}
    for msg in d.get("messages", []) or []:
        if not isinstance(msg, dict):
            continue
        try:
            round_no = int(msg.get("round", 0))
        except (TypeError, ValueError):
            continue
        by_round.setdefault(round_no, []).append(msg)
    return [{"round": r, "messages": by_round[r]} for r in sorted(by_round)]


def messages_view(state: DiscussionState | DiscussionResult | dict) -> list[dict]:
    """Raw message dicts incl. recipient_id (metadata) and timestamp when present."""
    d = _state_dict(state)
    out = []
    for msg in d.get("messages", []) or []:
        if not isinstance(msg, dict):
            continue
        meta = msg.get("metadata") or {}
        out.append(
            {
                "message_id": msg.get("message_id"),
                "discussion_id": msg.get(
                    "discussion_id", d.get("discussion_id")
                ),
                "agent_id": msg.get("agent_id"),
                "agent_name": msg.get("agent_name"),
                "round": msg.get("round"),
                "content": msg.get("content"),
                "recipient_id": meta.get("recipient_id"),  # None when router omits it
                "timestamp": msg.get("timestamp"),  # None only if core omits it
                "metadata": dict(meta),
            }
        )
    return out


def retrieval_context_view(
    state: DiscussionState | DiscussionResult | dict,
) -> list[dict]:
    """Available Week 1 context: retrieval_events + per-opinion evidence/sources."""
    d = _state_dict(state)
    events = [
        {
            "event_id": e.get("event_id"),
            "round": e.get("round"),
            "agent_id": e.get("agent_id"),
            "query": e.get("query"),
            "results": e.get("results", []),
        }
        for e in d.get("retrieval_events", []) or []
        if isinstance(e, dict)
    ]
    citations = []
    for agent_id, records in (d.get("opinions", {}) or {}).items():
        for rec in records or []:
            if not isinstance(rec, dict):
                continue
            citations.append(
                {
                    "agent_id": rec.get("agent_id", agent_id),
                    "round": rec.get("round"),
                    "evidence": list(rec.get("evidence", []) or []),
                    "sources": list(rec.get("sources", []) or []),
                }
            )
    return [{"retrieval_events": events, "opinion_citations": citations}]


__all__ = [
    "DEFAULT_PERSONAS",
    "MAX_ROUNDS",
    "DiscussionConfig",
    "DiscussionRequest",
    "DiscussionResult",
    "DiscussionState",
    "DiscussionStatus",
    "Message",
    "OpinionRecord",
    "RetrievalEvent",
    "agents_view",
    "rounds_view",
    "messages_view",
    "retrieval_context_view",
]
