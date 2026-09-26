from typing import Protocol, Any


class Memory(Protocol):
    def get_context(self) -> str:
        """Return recent conversation context as a string for prompt injection."""
        ...

    def add(self, role: str, content: str) -> None:
        """Store an interaction turn."""
        ...

    def clear(self) -> None:
        """Reset memory."""
        ...
