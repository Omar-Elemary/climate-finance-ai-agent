"""
Discussion context builder.

Constructs bounded, relevant context for each agent per round.
Agents receive only the information they need, preventing uncontrolled
token growth.
"""

import logging
from typing import Any

from .models import DiscussionState, Message, OpinionRecord

logger = logging.getLogger(__name__)


class DiscussionContextBuilder:
    """
    Builds discussion context for an agent at a specific round.

    Context includes:
    - Topic
    - Current round number
    - Previous discussion messages (bounded)
    - Messages from other agents in previous rounds
    - The agent's own previous opinion (if any)
    - Retrieved knowledge (if available)
    """

    def __init__(self, max_messages: int = 20) -> None:
        self.max_messages = max_messages

    def build(
        self,
        agent_id: str,
        agent_name: str,
        state: DiscussionState,
        retrieved_knowledge: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Build a context string for the agent at the current round.

        Args:
            agent_id: The agent's unique identifier.
            agent_name: The agent's human-readable name.
            state: Current discussion state.
            retrieved_knowledge: Optional retrieved knowledge chunks.

        Returns:
            A formatted context string for injection into the agent prompt.
        """
        parts: list[str] = []

        # Header
        parts.append(f"DISCUSSION TOPIC: {state.topic}")
        parts.append(f"CURRENT ROUND: {state.current_round} of {state.total_rounds}")
        parts.append(f"YOUR ROLE: {agent_name}")
        parts.append("")

        # Previous messages (bounded)
        previous_messages = state.get_all_previous_messages(before_round=state.current_round)
        if previous_messages:
            bounded = previous_messages[-self.max_messages :]
            parts.append("DISCUSSION HISTORY:")
            for msg in bounded:
                parts.append(f"  [{msg.agent_name}] (Round {msg.round}): {msg.content}")
            parts.append("")

        # Agent's own previous opinion
        own_opinions = state.get_opinion_history(agent_id)
        if own_opinions:
            latest = own_opinions[-1]
            parts.append(f"YOUR PREVIOUS OPINION (Round {latest.round}):")
            parts.append(f"  {latest.opinion}")
            parts.append("")

        # Retrieved knowledge
        if retrieved_knowledge:
            parts.append("RETRIEVED KNOWLEDGE:")
            for i, chunk in enumerate(retrieved_knowledge[:5], 1):
                text = chunk.get("chunk_text", "")
                source = chunk.get("source_url", "Unknown")
                parts.append(f"  [{i}] (Source: {source}): {text[:300]}")
            parts.append("")

        # Instructions
        parts.append("INSTRUCTIONS:")
        if state.current_round == 1:
            parts.append("  This is the opening round. Present your initial position on the topic.")
        else:
            parts.append(
                "  Consider the arguments made by other participants in previous rounds."
            )
            parts.append("  You may refine, challenge, or build upon earlier points.")
        parts.append("  Ground your response in evidence where possible.")

        return "\n".join(parts)

    def build_round_summary(self, state: DiscussionState, round_num: int) -> str:
        """
        Build a summary of a specific round for review.

        Args:
            state: Current discussion state.
            round_num: The round number to summarize.

        Returns:
            A summary string of the round's messages.
        """
        messages = state.get_messages_for_round(round_num)
        if not messages:
            return f"Round {round_num}: No messages."

        lines = [f"ROUND {round_num} SUMMARY:"]
        for msg in messages:
            lines.append(f"  {msg.agent_name}: {msg.content[:200]}")
        return "\n".join(lines)
