#!/usr/bin/env python
"""
Benchmark script to evaluate the Fossil Fuel Industry Agent's tool execution and memory across 8 LLMs.
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from src.agent import Agent
from src.llm import get_provider
from src.personas import load_persona
from src.tools import RetrievalTool, FinancialCalculatorTool, WebSearchTool
from src.memory import ConversationMemory

PERSONAS = ["Fossil Fuel Industry Agent"]

LLM_CONFIGS = [
    {"provider": "openrouter", "model": "liquid/lfm-2.5-2.6b:free"},
    {"provider": "openrouter", "model": "inclusionai/ling-3.0-flash-fin:free"},
    {"provider": "openrouter", "model": "nvidia/nemotron-3-super-120b-a12b:free"},
    {"provider": "openrouter", "model": "nvidia/nemotron-3-ultra-550b-a55b:free"},
    {"provider": "openrouter", "model": "openai/gpt-oss-120b"},
    {"provider": "openrouter", "model": "glm-5.3-flash"},
    {"provider": "gemini", "model": "gemini-3.7-flash"},
    {"provider": "openai_compat", "model": "qwen/qwen3.6-27b"} 
]

# The 3-turn gauntlet tests: 1. Retrieval, 2. Financial Math, 3. Context Memory
TEST_GAUNTLET = [
    {"type": "retrieval", "prompt": "Why should the government keep giving your industry subsidies when solar power is cheaper?"},
    {"type": "financial", "prompt": "roi 1000000 1400000"},
    {"type": "memory", "prompt": "Without searching the web or using tools, summarize the defense of subsidies you gave me in your very first answer."}
]

def run_tests():
    results = []
    original_model = os.getenv("LLM_MODEL")
    original_provider = os.getenv("LLM_PROVIDER")
    
    try:
        for config in LLM_CONFIGS:
            model = config["model"]
            provider = config["provider"]
            
            print(f"\n{'='*80}")
            print(f"Testing LLM: {model} (Provider: {provider})")
            print(f"{'='*80}")
            
            os.environ["LLM_PROVIDER"] = provider
            os.environ["LLM_MODEL"] = model
            
            if provider == "openai_compat":
                os.environ["LLM_BASE_URL"] = "https://api.groq.com/openai/v1"
                os.environ["LLM_API_KEY"] = os.getenv("GROQ_API_KEY", "")
            elif provider == "openrouter":
                if "LLM_BASE_URL" in os.environ:
                    del os.environ["LLM_BASE_URL"]
                os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "")
                os.environ["LLM_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "") 
            else:
                if "LLM_BASE_URL" in os.environ:
                    del os.environ["LLM_BASE_URL"]
                os.environ["LLM_API_KEY"] = os.getenv("GEMINI_API_KEY", "")
            
            try:
                llm = get_provider()
            except Exception as e:
                print(f"Error initializing LLM: {e}")
                continue
                
            for persona_name in PERSONAS:
                try:
                    persona = load_persona(persona_name)
                except Exception as e:
                    print(f"Error loading persona: {e}")
                    continue
                
                # Initialize fresh memory and all tools per model to prevent cross-contamination
                memory = ConversationMemory()
                tools = [RetrievalTool(), FinancialCalculatorTool(), WebSearchTool()]
                agent = Agent(persona=persona, llm=llm, memory=memory, tools=tools)
                
                model_run = {
                    "model": model,
                    "persona": persona_name,
                    "turns": []
                }
                
                for i, turn in enumerate(TEST_GAUNTLET):
                    print(f"\n--- Turn {i+1}: {turn['type'].upper()} TEST ---")
                    print(f"Prompt: {turn['prompt']}")
                    
                    turn_data = {"turn": i+1, "type": turn["type"], "prompt": turn["prompt"]}
                    
                    try:
                        # Handle specific ROI tool trigger format
                        if turn["prompt"].startswith("roi "):
                            parts = turn["prompt"].split()
                            initial = float(parts[1])
                            final = float(parts[2])
                            result = agent.generate_opinion(
                                f"What is the ROI? (initial={initial}, final={final})",
                                calculation="roi", initial_investment=initial, final_value=final
                            )
                        else:
                            result = agent.generate_opinion(turn["prompt"])
                            
                        turn_data["opinion"] = result.get("opinion", "")
                       # Safely handle None values from tools
                        sources = result.get("sources") or []
                        web_results = result.get("web_results") or []
                        
                        turn_data["tools_triggered"] = {
                            "calculation": result.get("calculation"),
                            "sources": len(sources),
                            "web_results": len(web_results)
                        }
                        print(f"Success! Response Length: {len(turn_data['opinion'])} chars")
                        
                    except Exception as e:
                        print(f"Failed: {e}")
                        turn_data["error"] = str(e)
                        
                    model_run["turns"].append(turn_data)
                    time.sleep(2) # Prevent rate limiting between turns
                    
                results.append(model_run)
                
    finally:
        if original_model:
            os.environ["LLM_MODEL"] = original_model
        if original_provider:
            os.environ["LLM_PROVIDER"] = original_provider
            
    return results

def save_results(results):
    output_file = "my_test_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {output_file}")
    
def generate_report(results):
    report_path = "docs/personas_llms_test_report.md"
    os.makedirs("docs", exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Model Benchmark: Multi-Turn Memory & Tool Use\n\n")
        f.write(f"- **Persona Tested:** {PERSONAS[0]}\n")
        f.write(f"- **Models Evaluated:** {len(LLM_CONFIGS)}\n\n")
        
        for r in results:
            f.write(f"## {r['model']}\n")
            for t in r["turns"]:
                f.write(f"**Turn {t['turn']} ({t['type']} test):**\n")
                if "error" in t:
                    f.write(f"- ❌ Error: `{t['error']}`\n\n")
                else:
                    tools = t["tools_triggered"]
                    f.write(f"- ✅ Success (Tools used: Math={bool(tools['calculation'])}, Docs={tools['sources']}, Web={tools['web_results']})\n")
                    f.write(f"- *Response excerpt:* {t['opinion'][:150]}...\n\n")
            f.write("---\n\n")
            
    print(f"Report generated: {report_path}")

if __name__ == "__main__":
    print("Starting Multi-Turn Benchmark...")
    results = run_tests()
    if results:
        save_results(results)
        generate_report(results)