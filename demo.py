#!/usr/bin/env python
"""
Interactive demo: run the full agent (persona + memory + tools) as a chat loop.

Usage:
    python demo.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from src.agent import Agent
from src.llm import get_provider
from src.personas import load_persona, list_personas
from src.tools import RetrievalTool, FinancialCalculatorTool, WebSearchTool
from src.memory import ConversationMemory


def choose_persona() -> str:
    try:
        available = list_personas()
    except Exception:
        available = []

    if not available:
        return input("Persona name to load: ").strip()

    print("\nAvailable personas:")
    for i, name in enumerate(available, 1):
        print(f"  {i}. {name}")

    choice = input(f"Choose a persona (1-{len(available)}), or type its name: ").strip()

    if choice.isdigit() and 1 <= int(choice) <= len(available):
        return available[int(choice) - 1]
    return choice


def main():
    print("=" * 70)
    print("Climate Finance Agent — Interactive Demo")
    print("=" * 70)

    persona_name = choose_persona()

    try:
        persona = load_persona(persona_name)
    except Exception as e:
        print(f"Could not load persona '{persona_name}': {e}")
        return

    # Force a model known to behave well with tool descriptions
    # (some free models hallucinate <tool_call> text even when no tools apply).
    forced_model = os.getenv("DEMO_MODEL", "inclusionai/ling-3.0-flash-fin:free")
    os.environ["LLM_MODEL"] = forced_model

    llm = get_provider()
    memory = ConversationMemory()

    agent = Agent(
        persona=persona,
        llm=llm,
        memory=memory,
        tools=[RetrievalTool(), FinancialCalculatorTool(), WebSearchTool()],
    )

    print(f"\nLoaded persona: {persona.name}")
    print(f"Using model: {llm.provider_name}/{llm.model}")
    print("\nType a topic/question and press Enter.")
    print("Type 'roi <investment> <final_value>' to force a financial calculation.")
    print("Type 'memory' to print what the agent currently remembers.")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        if user_input.lower() == "memory":
            print("\n--- Current memory context ---")
            print(memory.get_context() or "(empty)")
            print("--- end ---\n")
            continue

        # Simple manual override: "roi 1000000 1400000"
        if user_input.lower().startswith("roi "):
            parts = user_input.split()
            try:
                initial_investment = float(parts[1])
                final_value = float(parts[2])
            except (IndexError, ValueError):
                print("Usage: roi <initial_investment> <final_value>\n")
                continue

            result = agent.generate_opinion(
                f"What is the ROI on this investment? (initial={initial_investment}, final={final_value})",
                calculation="roi",
                initial_investment=initial_investment,
                final_value=final_value,
            )
        else:
            result = agent.generate_opinion(user_input)

        print(f"\nAgent ({persona.name}):")
        print(result["opinion"])

        if result.get("calculation"):
            print(f"\n[Tool used: financial_calculator -> {result['calculation']}]")
        elif result.get("web_results"):
            print(f"\n[Tool used: web_search -> {len(result['web_results'])} results]")
        elif result.get("sources"):
            print(f"\n[Tool used: climate_knowledge_search -> {len(result['sources'])} sources]")

        print()


if __name__ == "__main__":
    main()