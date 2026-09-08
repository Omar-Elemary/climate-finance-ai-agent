from typing import List, Dict, Any
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

    def route(self, message: Dict[str, Any], state: Any) -> List[Dict[str, Any]]:
        """Routes the message to all neighbor recipients determined by the graph topology."""
        sender_id = message.get("agent_id", "")
        recipients = self.get_next_recipients(sender_id)

        # Distribute the message to connected neighbors
        routed_messages = []
        for r_id in recipients:
            msg_copy = message.copy()
            msg_copy["metadata"] = msg_copy.get("metadata", {})
            msg_copy["metadata"]["recipient_id"] = r_id
            routed_messages.append(msg_copy)

        return routed_messages or [message]
    