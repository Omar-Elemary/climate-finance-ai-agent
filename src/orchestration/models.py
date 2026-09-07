"""
Discussion data models.

All typed data structures for the discussion orchestration layer.
Uses dataclasses to match Week 2 conventions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DiscussionStatus(str, Enum):
    """Lifecycle status of a discussion."""

    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Message:
    """A single message exchanged during the discussion."""

    message_id: str
    discussion_id: str
    round: int
    agent_id: str
    agent_name: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    in_response_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "discussion_id": self.discussion_id,
            "round": self.round,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "in_response_to": self.in_response_to,
            "metadata": self.metadata,
        }


@dataclass
class RetrievalEvent:
    """Records a retrieval event that occurred during discussion."""

    event_id: str
    discussion_id: str
    round: int
    agent_id: str
    query: str
    results: list[dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "discussion_id": self.discussion_id,
            "round": self.round,
            "agent_id": self.agent_id,
            "query": self.query,
            "results": self.results,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class OpinionRecord:
    """Tracks an agent's opinion at a specific round."""

    agent_id: str
    agent_name: str
    round: int
    opinion: str
    evidence: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "round": self.round,
            "opinion": self.opinion,
            "evidence": self.evidence,
            "sources": self.sources,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class DiscussionConfig:
    """Configuration for a discussion run."""

    num_rounds: int = 3
    max_messages_per_agent: int | None = None
    enable_retrieval: bool = True
    enable_opinion_tracking: bool = True
    context_max_messages: int = 20
    retrieval_query_template: str = (
        "Based on the topic '{topic}', provide a focused analysis."
    )


@dataclass
class DiscussionState:
    """Complete state of a discussion, mutated by the orchestrator."""

    discussion_id: str
    topic: str
    participants: list[str] = field(default_factory=list)
    current_round: int = 0
    total_rounds: int = 3
    status: DiscussionStatus = DiscussionStatus.INITIALIZED
    messages: list[Message] = field(default_factory=list)
    opinions: dict[str, list[OpinionRecord]] = field(default_factory=dict)
    retrieval_events: list[RetrievalEvent] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    error: str | None = None

    def add_message(self, message: Message) -> None:
        self.messages.append(message)

    def add_opinion(self, record: OpinionRecord) -> None:
        if record.agent_id not in self.opinions:
            self.opinions[record.agent_id] = []
        self.opinions[record.agent_id].append(record)

    def add_retrieval_event(self, event: RetrievalEvent) -> None:
        self.retrieval_events.append(event)

    def get_messages_for_round(self, round_num: int) -> list[Message]:
        return [m for m in self.messages if m.round == round_num]

    def get_all_previous_messages(self, before_round: int) -> list[Message]:
        return [m for m in self.messages if m.round < before_round]

    def get_opinion_history(self, agent_id: str) -> list[OpinionRecord]:
        return self.opinions.get(agent_id, [])

    def to_dict(self) -> dict[str, Any]:
        return {
            "discussion_id": self.discussion_id,
            "topic": self.topic,
            "participants": self.participants,
            "current_round": self.current_round,
            "total_rounds": self.total_rounds,
            "status": self.status.value,
            "messages": [m.to_dict() for m in self.messages],
            "opinions": {
                aid: [o.to_dict() for o in records]
                for aid, records in self.opinions.items()
            },
            "retrieval_events": [e.to_dict() for e in self.retrieval_events],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }


@dataclass
class DiscussionResult:
    """Structured result returned by the orchestrator."""

    discussion_id: str
    topic: str
    participants: list[str]
    rounds_completed: int
    messages: list[Message]
    opinions: dict[str, list[OpinionRecord]]
    retrieval_events: list[RetrievalEvent]
    status: DiscussionStatus
    started_at: datetime
    completed_at: datetime | None
    error: str | None = None

    @classmethod
    def from_state(cls, state: DiscussionState) -> "DiscussionResult":
        return cls(
            discussion_id=state.discussion_id,
            topic=state.topic,
            participants=state.participants,
            rounds_completed=state.current_round,
            messages=state.messages,
            opinions=state.opinions,
            retrieval_events=state.retrieval_events,
            status=state.status,
            started_at=state.started_at,
            completed_at=state.completed_at,
            error=state.error,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "discussion_id": self.discussion_id,
            "topic": self.topic,
            "participants": self.participants,
            "rounds_completed": self.rounds_completed,
            "messages": [m.to_dict() for m in self.messages],
            "opinions": {
                aid: [o.to_dict() for o in records]
                for aid, records in self.opinions.items()
            },
            "retrieval_events": [e.to_dict() for e in self.retrieval_events],
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }
