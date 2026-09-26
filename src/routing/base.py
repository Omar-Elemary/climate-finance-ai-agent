from typing import Protocol, List, runtime_checkable

@runtime_checkable
class RouterProtocol(Protocol):
    """Protocol for routing messages between agents."""

    def get_next_recipients(self, current_agent_id: str) -> List[str]:
        """Determine valid next recipients for a given sender."""
        ...
        