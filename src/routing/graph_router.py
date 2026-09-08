from typing import List, Any
from src.graph.topology import AgentGraph
from src.orchestration.router import Router
from src.routing.base import RouterProtocol

class GraphRouter(Router, RouterProtocol):
    """Router that determines message flow based on an AgentGraph.

    Implements both the orchestrator's Router protocol (for message routing)
    and the legacy RouterProtocol (for backward compatibility).
    """

    def __init__(self, graph: AgentGraph):
        if not graph.is_strongly_connected():
            raise ValueError("Graph must be strongly connected to be used for routing.")
        self.graph = graph

    def route(
        self,
        message: dict[str, Any],
        graph: Any = None,
        state: Any = None,
    ) -> list[dict[str, Any]]:
        """
        Route an agent's message to its neighbors in the graph.

        Preserves sender identity and creates a message notification for each recipient.
        Each recipient receives a copy of the message indicating they should receive it.

        Args:
            message: The agent's response dict containing at minimum
                     agent_id, content, round.
            graph: The discussion graph structure (not used, self.graph is used instead).
            state: Current discussion state for routing context (not used in this implementation).

        Returns:
            List of message dicts to be processed as received by neighbors.
            Each dict contains at minimum: agent_id (sender), content, round.
            Recipient information is added in metadata for downstream tracking.
        """
        # Extract sender info from the message
        sender_id = message.get("agent_id")
        if sender_id is None:
            # If no agent_id in message, cannot route - return as-is
            return [message]

        # Get neighbors (recipients) from the graph
        recipients = self.graph.get_neighbors(sender_id)

        # If no neighbors, return the original message (no routing needed)
        if not recipients:
            return [message]

        # Create a message notification for each recipient
        # Each recipient gets notified that they received a message from the sender
        routed_messages = []
        for recipient_id in recipients:
            # Create a copy of the message for this recipient's perspective
            routed_message = message.copy()
            # Preserve the original sender as the agent_id (who sent the message)
            # Add recipient information to metadata for tracking who received it
            if "metadata" not in routed_message:
                routed_message["metadata"] = {}
            routed_message["metadata"].update({
                "routed": True,
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "original_message_id": message.get("message_id", "unknown")
            })
            routed_messages.append(routed_message)

        return routed_messages

    def get_next_recipients(self, current_agent_id: str) -> List[str]:
        """Determine valid next recipients for a given sender.

        This method maintains backward compatibility with the legacy RouterProtocol.

        Args:
            current_agent_id: The ID of the sending agent.

        Returns:
            List of agent IDs that can receive messages from the sender.
        """
        return self.graph.get_neighbors(current_agent_id)
    