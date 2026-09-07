from typing import List
from src.graph.topology import AgentGraph
from src.routing.base import RouterProtocol

class GraphRouter(RouterProtocol):
    """Router that determines message flow based on an AgentGraph."""

    def __init__(self, graph: AgentGraph):
        if not graph.is_strongly_connected():
            raise ValueError("Graph must be strongly connected to be used for routing.")
        self.graph = graph

    def get_next_recipients(self, current_agent_id: str) -> List[str]:
        return self.graph.get_neighbors(current_agent_id)
    