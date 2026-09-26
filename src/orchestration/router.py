"""
Router Protocol — interface for graph-based message routing.

The orchestrator depends on this abstraction, NOT on the concrete
graph/routing algorithm. Any router that implements this protocol
can be injected.

OWNER: Member 3 or designated graph/routing member
STATUS: Protocol defined. No production implementation exists yet.
"""

from typing import Protocol, Any


class Router(Protocol):
    """Protocol for routing agent messages through the discussion graph."""

    def route(
        self,
        message: dict[str, Any],
        graph: Any = None,
        state: Any = None,
    ) -> list[dict[str, Any]]:
        """
        Route an agent's message and return messages to deliver.

        Args:
            message: The agent's response dict containing at minimum
                     agent_id, content, round.
            graph: The discussion graph structure (owned by another member).
            state: Current discussion state for routing context.

        Returns:
            List of routed message dicts to be added to the discussion.
            Each dict should contain at minimum: agent_id, content, round.
        """
        ...


class PassthroughRouter:
    """
    Default router that passes messages through unchanged.

    Use this when no graph-based routing is configured.
    The message is returned as-is in a single-element list.
    """

    def route(
        self,
        message: dict[str, Any],
        graph: Any = None,
        state: Any = None,
    ) -> list[dict[str, Any]]:
        return [message]
