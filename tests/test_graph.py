import pytest
from src.graph.topology import AgentGraph
from src.routing.graph_router import GraphRouter

def test_ring_topology_is_strongly_connected():
    agents = ["investor", "auditor", "ngo", "regulator"]
    graph = AgentGraph.create_ring_topology(agents)
    
    assert graph.is_strongly_connected() is True
    assert graph.get_neighbors("investor") == ["auditor"]
    assert graph.get_neighbors("regulator") == ["investor"]

def test_broken_graph_fails_validation():
    graph = AgentGraph()
    # Path: A -> B -> C (C cannot route back to A)
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    
    assert graph.is_strongly_connected() is False
    with pytest.raises(ValueError, match="Graph must be strongly connected"):
        GraphRouter(graph)

def test_graph_serialization_inspectable():
    agents = ["investor", "regulator"]
    graph = AgentGraph.create_ring_topology(agents)
    data = graph.to_dict()
    
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) == 2
    assert {"source": "investor", "target": "regulator"} in data["edges"]
    assert {"source": "regulator", "target": "investor"} in data["edges"]

def test_graph_router_routing():
    agents = ["A", "B", "C"]
    graph = AgentGraph.create_ring_topology(agents)
    router = GraphRouter(graph)
    
    assert router.get_next_recipients("A") == ["B"]
    assert router.get_next_recipients("C") == ["A"]

def test_persona_based_topology():
    climate_agents = [
        "cfo_agent",
        "policy_expert",
        "env_specialist",
        "industry_representative"
    ]
    graph = AgentGraph.create_persona_based_topology(climate_agents)
    
    assert graph.is_strongly_connected() is True
    assert "policy_expert" in graph.get_neighbors("cfo_agent")
    assert "cfo_agent" in graph.get_neighbors("env_specialist")