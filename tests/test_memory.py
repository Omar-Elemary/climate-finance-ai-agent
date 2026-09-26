import pytest
from src.memory.hybrid import AgentMemory

def test_hybrid_memory_retention():
    """Test that agent memory retains structured facts and conversation history across interactions."""
    memory = AgentMemory()
    
    # Interaction 1: Information introduced
    user_input_1 = "We are planning a climate project in Alexandria with a budget of $500,000."
    memory.add_interaction("user", user_input_1)
    
    # Extract and store structured facts
    memory.store_fact("project_region", "Alexandria")
    memory.store_fact("budget", "$500,000")
    
    agent_response_1 = "Registered project for Alexandria with $500,000."
    memory.add_interaction("assistant", agent_response_1)
    
    # Assertions for Interaction 1 storage
    assert memory.get_fact("project_region") == "Alexandria"
    assert memory.get_fact("budget") == "$500,000"
    
    # Interaction 2: Later interaction utilizing earlier stored information
    user_input_2 = "What is our target budget and region?"
    memory.add_interaction("user", user_input_2)
    
    # Agent uses memory
    region = memory.get_fact("project_region")
    budget = memory.get_fact("budget")
    
    agent_response_2 = f"Your target region is {region} and your budget is {budget}."
    memory.add_interaction("assistant", agent_response_2)
    
    # Acceptance criteria assertions
    context = memory.get_full_context()
    assert len(context["history"]) == 4  # 2 user + 2 assistant messages
    assert "Alexandria" in agent_response_2
    assert "$500,000" in agent_response_2