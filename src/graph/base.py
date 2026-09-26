from typing import Protocol, List, Dict, Any, runtime_checkable

@runtime_checkable
class AgentGraphProtocol(Protocol):
    """Protocol defining the interface for an Agent Graph."""

    def add_node(self, node_id: str) -> None:
        """Add an agent node to the graph."""
        ...

    def add_edge(self, source: str, target: str) -> None:
        """Add a directed edge from source agent to target agent."""
        ...

    def get_neighbors(self, node_id: str) -> List[str]:
        """Return outgoing neighbors for a given agent."""
        ...

    def is_strongly_connected(self) -> bool:
        """Verify if every agent can eventually reach every other agent."""
        ...

    def to_dict(self) -> Dict[str, Any]:
        """Export graph structure for inspection and reproducibility."""
        ...