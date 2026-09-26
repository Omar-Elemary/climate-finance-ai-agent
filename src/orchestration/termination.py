"""
Termination policies — determine when a discussion should stop.

The orchestrator checks termination after each round.
Additional policies (consensus, timeout, token budget) can be added
by implementing TerminationPolicy.
"""

import logging
from typing import Protocol

from .models import DiscussionState

logger = logging.getLogger(__name__)


class TerminationPolicy(Protocol):
    """Protocol for discussion termination decisions."""

    def should_terminate(self, state: DiscussionState) -> bool:
        """
        Decide whether the discussion should stop.

        Args:
            state: Current discussion state.

        Returns:
            True if the discussion should terminate, False to continue.
        """
        ...


class MaxRoundsTermination:
    """
    Terminates after a configured number of rounds.

    This is the default termination policy for Week 3.
    """

    def should_terminate(self, state: DiscussionState) -> bool:
        terminate = state.current_round >= state.total_rounds
        if terminate:
            logger.info(
                "Termination: reached max rounds (%d/%d)",
                state.current_round,
                state.total_rounds,
            )
        return terminate

    def __repr__(self) -> str:
        return "MaxRoundsTermination()"
