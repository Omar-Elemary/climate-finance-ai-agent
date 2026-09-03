import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    role: str          # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ConversationMemory:
    """
    Simple persistent-within-session conversation memory.

    Strategy: full conversation history (no summarization, no vector search).
    Every interaction (user message + assistant response) is stored in order
    and replayed as context on every subsequent call to the LLM.

    This satisfies the Week 2 requirement:
    - Receive an interaction -> add()
    - Store or retain relevant information -> self.history
    - Receive a later interaction -> add() again
    - Use information from the earlier interaction -> get_context()

    Known limitations (documented per assignment requirement):
    - Memory is in-process only; it is lost when the Python process ends
      (no persistent storage like a database or file, unless save()/load()
      below are used explicitly).
    - No summarization: long conversations will grow the prompt size linearly,
      which can eventually hit the LLM's context window limit and increase cost.
    - No semantic retrieval: all history is included verbatim, there is no
      selection of "most relevant" past turns (unlike vector-based memory).
    - Not thread-safe / not multi-user: intended for a single agent instance
      handling one conversation thread at a time.
    """

    def __init__(self, max_turns: int | None = None):
        """
        max_turns: optional cap on how many (user+assistant) turn-pairs to keep.
                   None = keep everything (simplest, but can grow unbounded).
        """
        self.history: list[MemoryEntry] = []
        self.max_turns = max_turns

    def add(self, role: str, content: str) -> None:
        """Store a new piece of the conversation (Interaction N)."""
        self.history.append(MemoryEntry(role=role, content=content))
        logger.debug("Memory: stored %s message (%d chars)", role, len(content))

        if self.max_turns is not None:
            # Each turn = 1 user + 1 assistant message = 2 entries
            max_entries = self.max_turns * 2
            if len(self.history) > max_entries:
                self.history = self.history[-max_entries:]

    def get_context(self) -> str:
        """
        Return the stored history as plain text, to be injected into the
        system prompt so a later interaction can use it (Interaction N+1).
        """
        if not self.history:
            return ""

        lines = []
        for entry in self.history:
            speaker = "User" if entry.role == "user" else "Agent"
            lines.append(f"{speaker}: {entry.content}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Reset memory (e.g. to start a new conversation thread)."""
        self.history = []

    def to_dict(self) -> list[dict[str, Any]]:
        """Export memory for saving/inspection."""
        return [
            {"role": e.role, "content": e.content, "timestamp": e.timestamp}
            for e in self.history
        ]

    @classmethod
    def from_dict(cls, data: list[dict[str, Any]]) -> "ConversationMemory":
        """Restore memory from a previously exported dict (simple persistence)."""
        memory = cls()
        memory.history = [
            MemoryEntry(role=d["role"], content=d["content"], timestamp=d.get("timestamp", ""))
            for d in data
        ]
        return memory