"""
Serialization helpers for the persistence layer.

`orchestration/models.py` (shared, owned by Omar) provides `to_dict()`
on every dataclass — the direction "object -> JSON-safe dict".
This module provides the REVERSE direction ("dict -> object"), which
is what `load()` needs to reconstruct a full DiscussionState after
reading it back from disk/DB. This keeps orchestration/models.py
untouched while still giving persistence full reconstruction ability.
"""

from datetime import datetime

from ..orchestration.models import (
    DiscussionState,
    DiscussionStatus,
    Message,
    OpinionRecord,
    RetrievalEvent,
)


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def message_from_dict(data: dict) -> Message:
    return Message(
        message_id=data["message_id"],
        discussion_id=data["discussion_id"],
        round=data["round"],
        agent_id=data["agent_id"],
        agent_name=data["agent_name"],
        content=data["content"],
        timestamp=_parse_dt(data["timestamp"]),
        in_response_to=data.get("in_response_to"),
        metadata=data.get("metadata", {}),
    )


def retrieval_event_from_dict(data: dict) -> RetrievalEvent:
    return RetrievalEvent(
        event_id=data["event_id"],
        discussion_id=data["discussion_id"],
        round=data["round"],
        agent_id=data["agent_id"],
        query=data["query"],
        results=data.get("results", []),
        timestamp=_parse_dt(data["timestamp"]),
    )


def opinion_record_from_dict(data: dict) -> OpinionRecord:
    return OpinionRecord(
        agent_id=data["agent_id"],
        agent_name=data["agent_name"],
        round=data["round"],
        opinion=data["opinion"],
        evidence=data.get("evidence", []),
        sources=data.get("sources", []),
        timestamp=_parse_dt(data["timestamp"]),
    )


def discussion_state_from_dict(data: dict) -> DiscussionState:
    """Reconstruct a full DiscussionState from its to_dict() output."""
    state = DiscussionState(
        discussion_id=data["discussion_id"],
        topic=data["topic"],
        participants=data.get("participants", []),
        current_round=data.get("current_round", 0),
        total_rounds=data.get("total_rounds", 3),
        status=DiscussionStatus(data.get("status", "initialized")),
        started_at=_parse_dt(data.get("started_at")),
        completed_at=_parse_dt(data.get("completed_at")),
        error=data.get("error"),
    )

    state.messages = [message_from_dict(m) for m in data.get("messages", [])]

    state.opinions = {
        agent_id: [opinion_record_from_dict(o) for o in records]
        for agent_id, records in data.get("opinions", {}).items()
    }

    state.retrieval_events = [
        retrieval_event_from_dict(e) for e in data.get("retrieval_events", [])
    ]

    return state