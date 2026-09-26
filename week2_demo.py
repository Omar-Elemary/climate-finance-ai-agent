#!/usr/bin/env python
"""
Week 2 Demo — Multi-Persona Agent Demonstration

Runs the same Agent implementation with different personas to show
that persona information is injected through configuration, not code.

Usage:
    python week2_demo.py                          # uses env vars for LLM config
    python week2_demo.py --provider openrouter    # override provider
    python week2_demo.py --persona investor       # single persona
"""
import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from src.agent import Agent
from src.llm import get_provider
from src.personas import load_persona, list_personas
from src.tools import RetrievalTool


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def format_opinion(result: dict) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append(f"PERSONA: {result['persona']}")
    lines.append(f"TOPIC: {result['topic']}")
    lines.append(f"PROVIDER: {result['provider']} / {result['model']}")
    lines.append("=" * 70)
    lines.append("")
    lines.append("OPINION:")
    lines.append(result["opinion"])
    lines.append("")
    if result["sources"]:
        lines.append("-" * 70)
        lines.append("SOURCES:")
        for src in result["sources"]:
            lines.append(f"  - {src}")
    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Week 2 Multi-Persona Agent Demo")
    parser.add_argument("--provider", default=None, help="LLM provider override")
    parser.add_argument("--persona", default=None, help="Single persona to use")
    parser.add_argument("--topic", default=None, help="Topic for opinion generation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger("week2_demo")

    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider

    try:
        llm = get_provider()
    except ValueError as e:
        print(f"LLM Provider Error: {e}")
        print("Set LLM_PROVIDER and LLM_API_KEY in your .env file.")
        sys.exit(1)

    print(f"\nLLM Provider: {llm.provider_name} / {llm.model}")
    print(f"Temperature: {llm.temperature}")

    retrieval_tool = RetrievalTool()

    if args.persona:
        persona_names = [args.persona]
    else:
        persona_names = list_personas()
        if not persona_names:
            print("No personas found in personas/ directory.")
            sys.exit(1)

    topic = args.topic or (
        "Should developed countries significantly increase "
        "climate adaptation finance for developing nations?"
    )

    print(f"\nTopic: {topic}")
    print(f"Personas: {persona_names}")
    print()

    for name in persona_names:
        try:
            persona = load_persona(name)
        except FileNotFoundError as e:
            print(f"Skipping persona '{name}': {e}")
            continue

        agent = Agent(persona=persona, llm=llm, tools=[retrieval_tool])

        print(f"\n{'#' * 70}")
        print(f"# Running Agent with persona: {persona.name}")
        print(f"{'#' * 70}\n")

        result = agent.generate_opinion(topic)
        print(format_opinion(result))
        print()


if __name__ == "__main__":
    main()
