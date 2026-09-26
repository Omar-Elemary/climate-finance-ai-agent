# src/orchestration — Week 3 Discussion Orchestrator

"""
Discussion orchestration layer for multi-agent collaboration.

This module coordinates multi-round discussions between agents,
managing lifecycle, context, scheduling, opinion tracking, and persistence.

Owner: Member 2 — Discussion Orchestration
"""

from .models import (
    DiscussionState,
    DiscussionConfig,
    DiscussionResult,
    Message,
    RetrievalEvent,
    OpinionRecord,
    DiscussionStatus,
)
from .orchestrator import DiscussionOrchestrator
from .context import DiscussionContextBuilder
from .scheduler import SequentialScheduler, AgentScheduler
from .termination import MaxRoundsTermination, TerminationPolicy
from .persistence import DiscussionPersistence, InMemoryPersistence
from .router import Router, PassthroughRouter
from .retriever import Retriever

__all__ = [
    # Core
    "DiscussionOrchestrator",
    # Models
    "DiscussionState",
    "DiscussionConfig",
    "DiscussionResult",
    "Message",
    "RetrievalEvent",
    "OpinionRecord",
    "DiscussionStatus",
    # Components
    "DiscussionContextBuilder",
    "SequentialScheduler",
    "AgentScheduler",
    "MaxRoundsTermination",
    "TerminationPolicy",
    "DiscussionPersistence",
    "InMemoryPersistence",
    "Router",
    "PassthroughRouter",
    "Retriever",
]
