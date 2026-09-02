# Week 2 — Core Agent Architecture

## Overview

Week 2 extends the Week 1 RAG pipeline with a **reusable, persona-agnostic Agent framework**. The Agent is the central abstraction that orchestrates persona, memory, tools, and LLM generation.

```
                    Persona (JSON config)
                       │
                       ▼
                 ┌───────────┐
                 │   Agent   │
                 └─────┬─────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Memory        Tools        LLM
       (interface)  (registry)  (provider)
          │            │            │
          │            ▼            │
          │       Week 1 RAG       │
          │       (RetrievalTool)  │
          │            │            │
          │            ▼            │
          │         Evidence        │
          └────────────┼────────────┘
                       ▼
                Context Builder
                       │
                       ▼
                 LLM Generation
                       │
                       ▼
                    Response
```

## Files Created

```
src/
├── __init__.py
├── agent.py                  # Core Agent class
├── llm/
│   ├── __init__.py           # Auto-discovery + provider registry
│   ├── base.py               # LLMProvider abstract class
│   ├── openrouter.py         # OpenRouter provider
│   ├── gemini.py             # Gemini provider
│   └── openai_compat.py      # Generic OpenAI-compatible (Ollama, vLLM, Anthropic, OpenAI)
├── memory/
│   └── base.py               # Memory interface (Protocol)
├── tools/
│   ├── __init__.py
│   ├── base.py               # Tool abstract class
│   └── retrieval.py          # RetrievalTool adapter for Week 1
├── prompts/
│   └── builder.py            # Context/message assembler
└── personas/
    ├── __init__.py
    ├── base.py               # Persona dataclass
    └── loader.py             # Load personas from JSON files

personas/
├── investor.json             # Sample: Climate Investor persona
├── policy_expert.json        # Sample: Policy Expert persona
└── scientist.json            # Sample: Environmental Scientist persona

week2_demo.py                 # Multi-persona demo entry point
tests/
├── test_agent.py
├── test_llm.py
├── test_tool.py
├── test_personas.py
└── test_prompts.py
docs/
└── architecture.md           # This file
```

## LLM Architecture

### Provider Abstraction

```python
# src/llm/base.py
class LLMProvider(ABC):
    def generate(self, messages: list[dict], **kwargs) -> LLMResponse: ...
    def from_env(cls) -> "LLMProvider": ...  # class method
```

### Supported Providers

| Provider | Name in `LLM_PROVIDER` | API Key Env Var | Default Model |
|----------|------------------------|-----------------|---------------|
| OpenRouter | `openrouter` | `LLM_API_KEY` or `OPENROUTER_API_KEY` | `anthropic/claude-3.5-sonnet` |
| OpenAI | `openai` | `LLM_API_KEY` or `OPENAI_API_KEY` | `gpt-4o-mini` |
| Gemini | `gemini` | `LLM_API_KEY` or `GEMINI_API_KEY` | `gemini-3.5-flash` |
| Ollama | `ollama` | `LLM_API_KEY` (can be dummy) | `llama3.1` |
| Anthropic | `anthropic` | `LLM_API_KEY` or `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-20241022` |
| OpenAI-compat | `openai_compat` | `LLM_API_KEY` | `gpt-4o-mini` |

### Auto-Discovery

Providers are auto-discovered from `src/llm/*.py`. To add a new provider:

1. Create `src/llm/my_provider.py`
2. Subclass `LLMProvider`
3. Set `provider_name = "my_provider"`
4. Implement `generate()` and `_default_model()`

The provider is automatically available via `LLM_PROVIDER=my_provider`.

### Environment Variables

```bash
LLM_PROVIDER=openrouter          # Which provider to use
LLM_API_KEY=sk-or-...            # API key (generic)
LLM_MODEL=anthropic/claude-3.5-sonnet  # Model name
LLM_BASE_URL=                    # Optional base URL override
LLM_TEMPERATURE=0.2              # Temperature (default 0.2)
LLM_MAX_TOKENS=2048              # Max tokens (default 2048)
```

## Persona Interface

### JSON Format

```json
{
    "name": "Climate Investor",
    "description": "A senior climate finance investor...",
    "system_prompt": "You approach climate finance from an investment perspective...",
    "tone": "Analytical, data-driven",
    "focus_areas": ["ROI", "Risk", "Market trends"]
}
```

### Usage

```python
from src.personas import load_persona, list_personas

# List available personas
names = list_personas()  # ["investor", "policy_expert", "scientist"]

# Load a persona
persona = load_persona("investor")
print(persona.to_prompt_context())  # Injected into Agent's system message
```

### Adding New Personas

Create `personas/my_persona.json`:

```json
{
    "name": "My Custom Persona",
    "description": "...",
    "system_prompt": "...",
    "tone": "...",
    "focus_areas": ["area1", "area2"]
}
```

The Agent automatically discovers and can use any persona from the `personas/` directory.

## Memory Interface

```python
# src/memory/base.py
class Memory(Protocol):
    def get_context(self) -> str: ...
    def add(self, role: str, content: str) -> None: ...
    def clear(self) -> None: ...
```

### Usage

```python
from src.agent import Agent

# Agent works without memory
agent = Agent(persona=persona, llm=llm)

# Agent works with memory
agent = Agent(persona=persona, llm=llm, memory=my_memory)
```

Member 3 implements concrete `Memory` classes. The Agent depends only on the interface.

## Tool Interface

```python
# src/tools/base.py
class Tool(ABC):
    name: str
    description: str
    def run(self, **kwargs) -> ToolResult: ...
```

### Built-in Tools

**RetrievalTool** — adapts Week 1's `hybrid_search_with_metadata`:

```python
from src.tools import RetrievalTool

tool = RetrievalTool()
result = tool.run(query="climate finance")
# result.success = True
# result.data = [{source_url, chunk_text, rerank_score}, ...]
```

### Adding New Tools

```python
from src.tools.base import Tool, ToolResult

class CalculatorTool(Tool):
    name = "calculator"
    description = "Perform calculations"

    def run(self, expression: str = "", **kwargs) -> ToolResult:
        try:
            result = eval(expression)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

## Agent API

### Initialization

```python
from src.agent import Agent
from src.personas import load_persona
from src.llm import get_provider
from src.tools import RetrievalTool

persona = load_persona("investor")
llm = get_provider()  # reads LLM_PROVIDER from env
tools = [RetrievalTool()]

agent = Agent(persona=persona, llm=llm, tools=tools)
```

### respond()

Conversational response:

```python
response = agent.respond("What is climate adaptation finance?")
# Returns: str
```

### generate_opinion()

Structured initial opinion:

```python
opinion = agent.generate_opinion("Should developed countries increase climate finance?")
# Returns: {
#     "topic": "...",
#     "persona": "Climate Investor",
#     "opinion": "...",
#     "evidence": ["chunk1", "chunk2", ...],
#     "sources": ["https://...", ...],
#     "provider": "openrouter",
#     "model": "anthropic/claude-3.5-sonnet"
# }
```

## Week 3 Interface

Week 3 multi-agent system can use the Agent like this:

```python
from src.agent import Agent
from src.personas import load_persona
from src.llm import get_provider
from src.tools import RetrievalTool

llm = get_provider()
tools = [RetrievalTool()]

personas = ["investor", "policy_expert", "scientist"]
agents = []
for name in personas:
    p = load_persona(name)
    agents.append(Agent(persona=p, llm=llm, tools=tools))

# Week 3: agents can discuss with each other
for agent in agents:
    opinion = agent.generate_opinion("Climate adaptation finance")
    print(f"{opinion['persona']}: {opinion['opinion'][:100]}...")
```

### What Week 3 Does NOT Need to Know

- How memory works internally
- How retrieval works internally
- How the LLM API works internally
- How tools work internally
- How persona configuration works internally

The Agent hides all implementation details.

## Running the Demo

```bash
# Set up environment
cp .env.example .env
# Edit .env with your API key

# Run demo with all personas
python week2_demo.py

# Run with specific provider
python week2_demo.py --provider openrouter

# Run with specific persona
python week2_demo.py --persona investor

# Run with custom topic
python week2_demo.py --topic "Should fossil fuel subsidies be eliminated?"
```

## Running Tests

```bash
cd "E:\Tech\Hackathons\Fellowship\Week 2"
python -m pytest tests/ -v
```
