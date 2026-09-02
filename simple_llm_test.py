#!/usr/bin/env python
"""
Simple LLM test without retrieval tool dependency.
Tests basic LLM functionality with different models via Groq.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.llm import get_provider

# Test models
LLM_MODELS = [
    "inclusionai/ling-3.0-flash-fin:free"
]

def test_model(model_name):
    """Test a specific model with a simple prompt."""
    print(f"\nTesting model: {model_name}")
    print("-" * 50)
    
    # Set model in environment
    os.environ["LLM_MODEL"] = model_name
    
    try:
        llm = get_provider()
        print(f"Provider: {llm.provider_name}")
        print(f"Model: {llm.model}")
        
        # Simple test message
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is climate finance in one sentence?"}
        ]
        
        response = llm.generate(messages)
        print(f"Response: {response.text[:300]}...")
        print(f"Usage: {response.usage}")
        return True, response.text
        
    except Exception as e:
        print(f"Error: {e}")
        return False, str(e)

def main():
    """Run tests for all models."""
    results = {}
    
    # Save original model
    original_model = os.getenv("LLM_MODEL")
    
    for model in LLM_MODELS:
        success, response = test_model(model)
        results[model] = {
            "success": success,
            "response": response if success else None,
            "error": response if not success else None
        }
    
    # Restore original model
    if original_model:
        os.environ["LLM_MODEL"] = original_model
    elif "LLM_MODEL" in os.environ:
        del os.environ["LLM_MODEL"]
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for model, result in results.items():
        status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
        print(f"{model}: {status}")
        if result["error"]:
            print(f"  Error: {result['error'][:100]}...")
    
    return results

if __name__ == "__main__":
    main()