from typing import Dict, Set, List, Any, Optional
from src.graph.base import AgentGraphProtocol
from src.graph.validation import check_strong_connectivity

class AgentGraph(AgentGraphProtocol):
    def __init__(self, agent_ids: Optional[List[str]] = None):
        self.adjacency_list: Dict[str, Set[str]] = {}
        if agent_ids:
            for aid in agent_ids:
                self.add_node(aid)

    def add_node(self, node_id: str) -> None:
        if node_id not in self.adjacency_list:
            self.adjacency_list[node_id] = set()

    def add_edge(self, source: str, target: str) -> None:
        if source not in self.adjacency_list:
            self.add_node(source)
        if target not in self.adjacency_list:
            self.add_node(target)
        self.adjacency_list[source].add(target)

    def get_neighbors(self, node_id: str) -> List[str]:
        return sorted(list(self.adjacency_list.get(node_id, set())))

    def is_strongly_connected(self) -> bool:
        return check_strong_connectivity(self.adjacency_list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": sorted(list(self.adjacency_list.keys())),
            "edges": [
                {"source": u, "target": v}
                for u in sorted(self.adjacency_list.keys())
                for v in sorted(self.adjacency_list[u])
            ]
        }

    @classmethod
    def create_ring_topology(cls, agent_ids: List[str]) -> "AgentGraph":
        """Builds a strongly connected directed ring (A -> B -> C -> A)."""
        graph = cls(agent_ids)
        n = len(agent_ids)
        if n > 1:
            for i in range(n):
                graph.add_edge(agent_ids[i], agent_ids[(i + 1) % n])
        return graph

    @classmethod
    def create_fully_connected(cls, agent_ids: List[str]) -> "AgentGraph":
        """Builds a complete directed graph where every agent can reach everyone directly."""
        graph = cls(agent_ids)
        for u in agent_ids:
            for v in agent_ids:
                if u != v:
                    graph.add_edge(u, v)
        return graph
    @classmethod
    def create_persona_based_topology(cls, agent_ids: List[str]) -> "AgentGraph":
        """
        Creates a strongly connected graph reflecting the Climate Finance ecosystem.
        Connects financial stakeholders -> regulatory experts -> environmental/social advocates -> industry practitioners -> back to finance.
        """
        graph = cls(agent_ids)
        if not agent_ids:
            return graph

        # 1. Base cycle to guarantee strong connectivity across all participating agents
        n = len(agent_ids)
        if n > 1:
            for i in range(n):
                graph.add_edge(agent_ids[i], agent_ids[(i + 1) % n])

        # 2. Add domain-specific communication channels if specific agents exist
        def link_if_present(src: str, dst: str):
            if src in graph.adjacency_list and dst in graph.adjacency_list:
                graph.add_edge(src, dst)

        # Allow cross-functional consultations
        for a in agent_ids:
            for b in agent_ids:
                if a == b:
                    continue
                # Regulators and Industry cross-consultation
                if ("policy" in a or "regulator" in a) and ("industry" in b or "cfo" in b):
                    link_if_present(a, b)
                # Environmental specialists advise investors directly
                if "env" in a and ("investor" in b or "cfo" in b):
                    link_if_present(a, b)

        return graph