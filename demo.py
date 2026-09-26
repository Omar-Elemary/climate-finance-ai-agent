"""
Demo: Hybrid Agent Memory
--------------------------
Demonstrates that the agent can retain information introduced in an
earlier interaction and use it correctly in a later interaction.

Run:
    python demo.py
"""

from src.memory.hybrid import AgentMemory


def simple_extract_facts(memory: AgentMemory, text: str) -> None:
    """
    Very small heuristic extractor for the demo.
    (In production this would be replaced by an NLU/LLM-based extractor,
    as noted in the Limitations section of the memory strategy doc.)
    """
    if "Alexandria" in text:
        memory.store_fact("project_region", "Alexandria")
    if "$500,000" in text:
        memory.store_fact("budget", "$500,000")


def run_demo():
    memory = AgentMemory()

    # ------------------------------------------------------------------
    # Interaction 1: Information introduced
    # ------------------------------------------------------------------
    print("=== Interaction 1 ===")
    user_input_1 = "We are planning a climate project in Alexandria with a budget of $500,000."
    print(f"User: {user_input_1}")

    memory.add_interaction("user", user_input_1)
    simple_extract_facts(memory, user_input_1)

    agent_response_1 = "Got it — registered project for Alexandria with a budget of $500,000."
    memory.add_interaction("assistant", agent_response_1)
    print(f"Agent: {agent_response_1}\n")

    # ------------------------------------------------------------------
    # Interaction 2: Agent uses information from Interaction 1
    # ------------------------------------------------------------------
    print("=== Interaction 2 ===")
    user_input_2 = "What is our target budget and region?"
    print(f"User: {user_input_2}")

    memory.add_interaction("user", user_input_2)

    region = memory.get_fact("project_region")
    budget = memory.get_fact("budget")
    agent_response_2 = f"Your target region is {region} and your budget is {budget}."
    memory.add_interaction("assistant", agent_response_2)
    print(f"Agent: {agent_response_2}\n")

    # ------------------------------------------------------------------
    # Proof of retention
    # ------------------------------------------------------------------
    print("=== Verification ===")
    assert region == "Alexandria"
    assert budget == "$500,000"
    print("Agent correctly recalled facts from Interaction 1 while answering Interaction 2.")

    print("\nFull structured memory state:")
    print(memory.get_full_context()["structured_memory"])


if __name__ == "__main__":
    run_demo()