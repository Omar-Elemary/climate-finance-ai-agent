# Climate Finance RAG Agent — Week 2

> **Week 2 Focus:** Core Agent Architecture + LLM Abstraction + Generation Pipeline

## What Week 2 Adds

Week 2 extends the Week 1 RAG pipeline with a **reusable, persona-agnostic Agent framework**. The Agent is the central abstraction that orchestrates persona, memory, tools, and LLM generation — without being hardcoded to any specific provider or persona.

### Key Capabilities

1. **Configurable agents** — any persona, any LLM provider, any tool set
2. **Persistent memory** — interface for Member 3 to implement
3. **Tool access** — registry-based tool system with built-in retrieval adapter
4. **Week 1 retrieval integration** — thin adapter around `hybrid_search_with_metadata()`
5. **Grounded opinion generation** — structured output with evidence + sources
6. **Multi-provider LLM** — OpenRouter, OpenAI, Gemini, Ollama, Anthropic, or any OpenAI-compatible endpoint
7. **Reusable architecture** — supports multiple personas, ready for Week 3 multi-agent

---

## Architecture

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

---

## Files Added

```
src/
├── __init__.py
├── agent.py                  # Core Agent class
├── llm/
│   ├── __init__.py           # Auto-discovery + provider registry
│   ├── base.py               # LLMProvider abstract class + LLMResponse
│   ├── openrouter.py         # OpenRouter provider (via openai SDK)
│   ├── gemini.py             # Gemini provider (via google-genai SDK)
│   └── openai_compat.py      # Generic OpenAI-compatible + OpenAI + Ollama + Anthropic
├── memory/
│   └── base.py               # Memory protocol interface
├── tools/
│   ├── __init__.py           # Lazy-loading tools package
│   ├── base.py               # Tool abstract class + ToolResult
│   └── retrieval.py          # RetrievalTool adapter for Week 1
├── prompts/
│   └── builder.py            # Context/message assembler
└── personas/
    ├── __init__.py
    ├── base.py               # Persona dataclass
    └── loader.py             # Load personas from JSON files

personas/
├── investor.json             # Climate Investor persona
├── policy_expert.json        # Policy Expert persona
└── scientist.json            # Environmental Scientist persona

week2_demo.py                 # Multi-persona demo entry point
tests/
├── test_agent.py             # 8 tests
├── test_llm.py               # 7 tests
├── test_tool.py              # 6 tests
├── test_personas.py          # 6 tests
└── test_prompts.py           # 8 tests
docs/
└── architecture.md           # Detailed architecture documentation
requirements.txt              # Updated dependencies
.env.example                  # Updated with LLM config vars
```

**No existing files modified.** Week 1 remains untouched.

---

## LLM Providers

### Supported Providers

| Provider | `LLM_PROVIDER` value | Default Model | SDK |
|----------|---------------------|---------------|-----|
| OpenRouter | `openrouter` | `anthropic/claude-3.5-sonnet` | openai |
| OpenAI | `openai` | `gpt-4o-mini` | openai |
| Gemini | `gemini` | `gemini-3.5-flash` | google-genai |
| Ollama | `ollama` | `llama3.1` | openai (local) |
| Anthropic | `anthropic` | `claude-3-5-sonnet-20241022` | openai (compat) |
| Any OpenAI-compatible | `openai_compat` | `gpt-4o-mini` | openai |

### Auto-Discovery

Providers are auto-discovered from `src/llm/*.py`. To add a new provider:

1. Create `src/llm/my_provider.py`
2. Subclass `LLMProvider`
3. Set `provider_name = "my_provider"`
4. Implement `generate()` and `_default_model()`

The provider is immediately available via `LLM_PROVIDER=my_provider`.

### Environment Variables

```bash
# .env
LLM_PROVIDER=openrouter
LLM_API_KEY=sk-or-...
LLM_MODEL=anthropic/claude-3.5-sonnet
LLM_BASE_URL=              # optional override
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=2048
```

---

## Personas

Personas are JSON files in the `personas/` directory. The Agent loads them by name and injects the persona context into the system prompt.

### Example Persona (`personas/investor.json`)

```json
{
    "name": "Climate Investor",
    "description": "A senior climate finance investor with 15 years of experience...",
    "system_prompt": "You approach climate finance from an investment perspective...",
    "tone": "Analytical, data-driven, focused on returns and risk management.",
    "focus_areas": ["ROI and financial returns", "Risk assessment", "Market trends"]
}
```

### Adding a New Persona

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

### Usage

```python
from src.personas import load_persona, list_personas

# List available personas
names = list_personas()  # ["investor", "policy_expert", "scientist"]

# Load a persona
persona = load_persona("investor")
```

---

## Agent API

### Initialization

```python
from src.agent import Agent
from src.personas import load_persona
from src.llm import get_provider
from src.tools import RetrievalTool

persona = load_persona("investor")
llm = get_provider()  # reads from env vars
tools = [RetrievalTool()]

agent = Agent(persona=persona, llm=llm, tools=tools)
```

### respond() — Conversational

```python
response = agent.respond("What is climate adaptation finance?")
# Returns: str
```

### generate_opinion() — Structured

```python
opinion = agent.generate_opinion("Should developed countries increase climate finance?")
# Returns: {
#     "topic": "Should developed countries increase climate finance?",
#     "persona": "Climate Investor",
#     "opinion": "...",
#     "evidence": ["chunk1 text", "chunk2 text", ...],
#     "sources": ["https://...", ...],
#     "provider": "openrouter",
#     "model": "anthropic/claude-3.5-sonnet"
# }
```

---

## Tool System

### Adding a New Tool

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

Then pass it to the Agent:

```python
agent = Agent(persona=persona, llm=llm, tools=[RetrievalTool(), CalculatorTool()])
```

---

## Week 1 Integration

Week 2 wraps Week 1's `hybrid_search_with_metadata()` through a `RetrievalTool` adapter:

```python
# Week 1 (unchanged)
from retriever import hybrid_search_with_metadata
results = hybrid_search_with_metadata(query, top_k=30, rrf_k=60, final_k=3)

# Week 2 (adapter)
from src.tools import RetrievalTool
tool = RetrievalTool()
result = tool.run(query=query)
# result.success = True
# result.data = [{source_url, chunk_text, rerank_score}, ...]
```

The retrieval is lazy-loaded — it only imports the heavy Week 1 dependencies when the tool is actually used.

---

## Week 3 Interface

Week 3 multi-agent system can use the Agent like this:

```python
from src.agent import Agent
from src.personas import load_persona
from src.llm import get_provider
from src.tools import RetrievalTool

llm = get_provider()
tools = [RetrievalTool()]

# Create agents for different personas
agents = []
for name in ["investor", "policy_expert", "scientist"]:
    persona = load_persona(name)
    agents.append(Agent(persona=persona, llm=llm, tools=tools))

# Each agent generates grounded opinions independently
for agent in agents:
    opinion = agent.generate_opinion("Climate adaptation finance")
    print(f"{opinion['persona']}: {opinion['opinion'][:200]}...")
```

Week 3 does NOT need to know how memory, retrieval, LLM, tools, or personas work internally. The Agent hides all implementation details.

---

## Running

### Demo

```bash
# Set up environment
cp .env.example .env
# Edit .env with your API key

# Run with all personas
python week2_demo.py

# Run with specific provider
python week2_demo.py --provider openrouter

# Run with specific persona
python week2_demo.py --persona investor

# Run with custom topic
python week2_demo.py --topic "Should fossil fuel subsidies be eliminated?"

# Verbose logging
python week2_demo.py -v
```

### Tests

```bash
python -m pytest tests/ -v
```

---

## Week 1 Files (Untouched)

These files remain exactly as they were:

| File | Purpose |
|------|---------|
| `scraper.py` | Scrapes climate finance URLs |
| `chunker.py` | Chunks documents into overlapping segments |
| `embedder.py` | Creates embeddings + BM25 index |
| `setup_postgres.py` | Sets up PostgreSQL + pgvector |
| `retriever.py` | Hybrid search (BM25 + Vector + RRF + Cross-Encoder) |
| `rag_agent.py` | Week 1 agent (Gemini direct) |
| `evaluate_rag.py` | Retrieval evaluation |
| `bm25_index.pkl` | Pre-built BM25 index |
| `data/` | Raw documents + chunks |

---

## Notes

- **No hardcoded secrets** — all API keys via environment variables
- **No hardcoded personas** — persona info injected through JSON config
- **No hardcoded LLM providers** — provider selected at runtime via env var
- **Lazy imports** — heavy dependencies (torch, sentence_transformers) only loaded when retrieval tool is used
- **Clean interfaces** — Memory, Tool, LLMProvider are all abstract/protocol-based
- **Single responsibility** — each module does one thing
