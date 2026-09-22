"""Core-level exceptions — the public error contract for agent_core/.

The backend maps these to HTTP without modification::

    InvalidDiscussionRequest  -> 400 INVALID_REQUEST
    DiscussionNotFound        -> 404 DISCUSSION_NOT_FOUND
    RetrievalError            -> 503 SERVICE_UNAVAILABLE (dependency)
    AgentExecutionError       -> 503 SERVICE_UNAVAILABLE (dependency)
    DiscussionExecutionError  -> 503 SERVICE_UNAVAILABLE / 500 INTERNAL_ERROR

Raw third-party / internal exceptions are never part of the contract;
service.py chains them via ``raise ... from exc`` for logs only.
"""
from __future__ import annotations

from typing import Any


class CoreError(Exception):
    """Base for all public core failures."""

    def __init__(self, message: str, *, details: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class InvalidDiscussionRequest(CoreError):
    """Bad request: empty topic, bad num_rounds, unknown/duplicate personas."""


class DiscussionNotFound(CoreError):
    """No persisted discussion for the given id."""

    def __init__(self, discussion_id: str) -> None:
        super().__init__(
            f"Discussion '{discussion_id}' was not found.",
            details={"discussion_id": discussion_id},
        )
        self.discussion_id = discussion_id


class RetrievalError(CoreError):
    """Week 1 RAG subsystem unavailable or failed."""


class AgentExecutionError(CoreError):
    """LLM provider / agent construction failed (missing key, bad model, ...)."""


class DiscussionExecutionError(CoreError):
    """Orchestrator / graph / persistence failed mid-run."""
