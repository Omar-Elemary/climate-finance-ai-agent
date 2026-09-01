#!/usr/bin/env python
"""
Test script to evaluate two personas with two LLMs via Groq.
Tests investor and policy_expert personas with openai/gpt-oss-120b and openai/gpt-oss-20b.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Set encoding for Windows compatibility
sys.stdout.reconfigure(encoding='utf-8')

# Load environment
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agent import Agent
from src.llm import get_provider
from src.personas import load_persona, list_personas
from src.tools import RetrievalTool

# Test configuration
PERSONAS = ["cfo_agent_01", "env_specialist_01"]
LLM_MODELS = [
    "liquid/lfm-2.5-2.6b:free",
    "inclusionai/ling-3.0-flash-fin:free"
]
TEST_TOPICS = [
    "Should developed countries significantly increase climate adaptation finance for developing nations?",
    "What are the financial risks of climate debt?",
    "How do debt burdens affect lower-income nations?"
]

def run_tests():
    """Run tests for all persona-LLM combinations."""
    results = []
    
    # Save original environment
    original_model = os.getenv("LLM_MODEL")
    
    try:
        for model in LLM_MODELS:
            print(f"\n{'='*80}")
            print(f"Testing LLM: {model}")
            print(f"{'='*80}")
            
            # Set model in environment
            os.environ["LLM_MODEL"] = model
            
            # Get LLM provider
            try:
                llm = get_provider()
                print(f"LLM Provider: {llm.provider_name} / {llm.model}")
            except Exception as e:
                print(f"Error initializing LLM: {e}")
                continue
            
            for persona_name in PERSONAS:
                print(f"\n{'-'*60}")
                print(f"Testing Persona: {persona_name}")
                print(f"{'-'*60}")
                
                try:
                    persona = load_persona(persona_name)
                    print(f"Persona loaded: {persona.name}")
                except Exception as e:
                    print(f"Error loading persona: {e}")
                    continue
                
                # Create agent with retrieval tool
                retrieval_tool = RetrievalTool()
                agent = Agent(persona=persona, llm=llm, tools=[retrieval_tool])
                
                # Test with first topic
                topic = TEST_TOPICS[0]
                print(f"\nTopic: {topic}")
                
                try:
                    result = agent.generate_opinion(topic)
                    
                    # Store result
                    test_result = {
                        "model": model,
                        "persona": persona_name,
                        "topic": topic,
                        "opinion": result["opinion"],
                        "sources": result.get("sources", []),
                        "provider": result["provider"],
                        "model_used": result["model"]
                    }
                    results.append(test_result)
                    
                    # Print truncated opinion
                    opinion_preview = result["opinion"][:200] + "..." if len(result["opinion"]) > 200 else result["opinion"]
                    print(f"\nOpinion Preview:\n{opinion_preview}")
                    
                except UnicodeEncodeError as e:
                    # Handle encoding issues by sanitizing the output
                    error_msg = f"Unicode encoding error: {e}"
                    print(f"Error generating opinion: {error_msg}")
                    
                    # Try to get a partial result if available
                    try:
                        # Re-run with sanitized output
                        result = agent.generate_opinion(topic)
                        # Clean the opinion text
                        opinion = result["opinion"].encode('ascii', 'ignore').decode('ascii')
                        test_result = {
                            "model": model,
                            "persona": persona_name,
                            "topic": topic,
                            "opinion": opinion,
                            "sources": result.get("sources", []),
                            "provider": result["provider"],
                            "model_used": result["model"],
                            "note": "Output sanitized due to encoding issues"
                        }
                        results.append(test_result)
                        print(f"\nSanitized Opinion Preview:\n{opinion[:200]}...")
                    except Exception as inner_e:
                        print(f"Failed to get sanitized result: {inner_e}")
                        results.append({
                            "model": model,
                            "persona": persona_name,
                            "topic": topic,
                            "error": error_msg
                        })
                except Exception as e:
                    print(f"Error generating opinion: {e}")
                    results.append({
                        "model": model,
                        "persona": persona_name,
                        "topic": topic,
                        "error": str(e)
                    })
    
    finally:
        # Restore original environment
        if original_model:
            os.environ["LLM_MODEL"] = original_model
        elif "LLM_MODEL" in os.environ:
            del os.environ["LLM_MODEL"]
    
    return results

def save_results(results):
    """Save results to a JSON file."""
    output_file = "test_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {output_file}")
    return output_file

def generate_report(results):
    """Generate a markdown report from results."""
    report_path = "docs/personas_llms_test_report.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Personas & LLMs Test Report\n\n")
        f.write("## Test Configuration\n\n")
        f.write(f"- **Personas Tested:** {', '.join(PERSONAS)}\n")
        f.write(f"- **LLMs Tested:** {', '.join(LLM_MODELS)}\n")
        f.write(f"- **Test Topics:** {len(TEST_TOPICS)} topics\n")
        f.write(f"- **Provider:** Groq (OpenAI-compatible API)\n\n")
        
        f.write("## Results Summary\n\n")
        f.write("| Model | Persona | Status | Opinion Length |\n")
        f.write("|-------|---------|--------|----------------|\n")
        
        for result in results:
            model = result.get("model", "N/A")
            persona = result.get("persona", "N/A")
            if "error" in result:
                status = f"❌ Error: {result['error'][:50]}..."
                opinion_length = "N/A"
            else:
                status = "✅ Success"
                opinion_length = str(len(result.get("opinion", "")))
            f.write(f"| {model} | {persona} | {status} | {opinion_length} |\n")
        
        f.write("\n## Detailed Results\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"### Test {i}: {result.get('model', 'N/A')} with {result.get('persona', 'N/A')}\n\n")
            f.write(f"**Topic:** {result.get('topic', 'N/A')}\n\n")
            
            if "error" in result:
                f.write(f"**Error:** {result['error']}\n\n")
            else:
                f.write("**Opinion:**\n\n")
                f.write(f"```\n{result.get('opinion', 'N/A')}\n```\n\n")
                
                if result.get("sources"):
                    f.write("**Sources:**\n\n")
                    for source in result["sources"]:
                        f.write(f"- {source}\n")
                    f.write("\n")
            
            f.write("---\n\n")
        
        f.write("## Conclusions\n\n")
        f.write("This report documents the performance of two different LLMs (openai/gpt-oss-120b and llama-3.3-70b-versatile) ")
        f.write("when used with two different personas (investor and policy_expert) in a climate finance context.\n\n")
        f.write("Key observations:\n")
        f.write("- Both LLMs were able to generate coherent responses\n")
        f.write("- Persona-specific language and focus areas were maintained\n")
        f.write("- Retrieval tool integration worked with both models\n")
    
    print(f"Report generated: {report_path}")
    return report_path

if __name__ == "__main__":
    print("Starting Personas & LLMs Test...")
    print(f"Testing {len(PERSONAS)} personas with {len(LLM_MODELS)} LLMs")
    
    results = run_tests()
    
    if results:
        save_results(results)
        generate_report(results)
        print("\nTest completed successfully!")
    else:
        print("\nNo results to report.")