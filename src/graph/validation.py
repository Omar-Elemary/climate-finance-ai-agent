from typing import Dict, Set
from collections import deque

def check_strong_connectivity(adjacency_list: Dict[str, Set[str]]) -> bool:
    """
    Checks if a directed graph is strongly connected using BFS.
    A graph is strongly connected if every node can reach all other nodes.
    """
    nodes = list(adjacency_list.keys())
    if not nodes or len(nodes) == 1:
        return True

    def bfs(start_node: str, graph: Dict[str, Set[str]]) -> Set[str]:
        visited = set()
        queue = deque([start_node])
        visited.add(start_node)

        while queue:
            current = queue.popleft()
            for neighbor in graph.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited

    first_node = nodes[0]

    # 1. Check if first_node can reach all nodes
    visited_forward = bfs(first_node, adjacency_list)
    if len(visited_forward) != len(nodes):
        return False

    # 2. Reverse graph edges (Transpose Graph)
    reversed_graph: Dict[str, Set[str]] = {n: set() for n in nodes}
    for u in nodes:
        for v in adjacency_list[u]:
            reversed_graph[v].add(u)

    # 3. Check if first_node can reach all nodes in transposed graph
    visited_backward = bfs(first_node, reversed_graph)
    return len(visited_backward) == len(nodes)