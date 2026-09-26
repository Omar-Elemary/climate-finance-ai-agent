"""
Agent scheduler — determines which agents participate and in what order.

The scheduler is isolated so the project can later support:
- sequential scheduling (current)
- priority-based scheduling
- graph-driven scheduling
- selective agent activation
"""

import logging
from typing import Protocol, Any

logger = logging.getLogger(__name__)


class AgentScheduler(Protocol):
    """Protocol for agent scheduling strategies."""

    def get_agents_for_round(
        self,
        round_num: int,
        agents: list[Any],
    ) -> list[Any]:
        """
        Return the ordered list of agents for the given round.

        Args:
            round_num: The current round number (1-indexed).
            agents: All available agents.

        Returns:
            Ordered list of agents to participate in this round.
        """
        ...


class SequentialScheduler:
    """
    Deterministic sequential scheduler.

    Cycles through all agents in order for every round:
        Round 1: [A, B, C, D]
        Round 2: [A, B, C, D]
        Round 3: [A, B, C, D]

    This is the simplest scheduling strategy and the default for Week 3.
    """

    def get_agents_for_round(
        self,
        round_num: int,
        agents: list[Any],
    ) -> list[Any]:
        """Return all agents in their original order for every round."""
        logger.debug("SequentialScheduler: round %d, %d agents", round_num, len(agents))
        return list(agents)

    def __repr__(self) -> str:
        return "SequentialScheduler()"
