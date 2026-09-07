"""
Persistence Protocol — interface for saving/loading discussion state.

The orchestrator depends on this abstraction, NOT on the concrete
storage backend (PostgreSQL, file, etc.). Any persistence layer that
implements this protocol can be injected.

OWNER: Member 3 — Persistence / Storage
STATUS: Protocol defined. InMemoryPersistence provided as default.
"""

from typing import Protocol, Any
from .models import DiscussionState


class DiscussionPersistence(Protocol):
    """Protocol for persisting discussion state."""

    def save(self, state: DiscussionState) -> None:
        """
        Persist the current discussion state.

        Called at meaningful checkpoints:
        - Discussion initialization
        - After each round
        - Final discussion state

        Args:
            state: The current discussion state to persist.
        """
        ...

    def load(self, discussion_id: str) -> DiscussionState | None:
        """
        Load a discussion state by ID.

        Args:
            discussion_id: The unique discussion identifier.

        Returns:
            The DiscussionState if found, None otherwise.
        """
        ...


class InMemoryPersistence:
    """
    In-memory persistence for development and testing.

    Stores discussion states in a dict. Data is lost when the process exits.
    """

    def __init__(self) -> None:
        self._store: dict[str, DiscussionState] = {}

    def save(self, state: DiscussionState) -> None:
        self._store[state.discussion_id] = state

    def load(self, discussion_id: str) -> DiscussionState | None:
        return self._store.get(discussion_id)

    def exists(self, discussion_id: str) -> bool:
        return discussion_id in self._store

    def clear(self) -> None:
        self._store.clear()
