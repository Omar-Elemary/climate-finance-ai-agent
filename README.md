# Climate Finance AI Agent

> Grounded, multi-persona AI system for climate-finance questions — built week by week: RAG retrieval → configurable Agent → multi-agent discussion → discussion analytics.

| Week | Focus | Entry point |
|------|-------|-------------|
| [Week 1](#week-1--rag-pipeline) | Scrape → chunk → embed → hybrid retrieval → grounded generation | `rag_agent.py` |
| [Week 2](#week-2--core-agent) | Persona-agnostic `Agent` (persona + memory + tools + multi-provider LLM) | `week2_demo.py` |
| [Week 3](#week-3--multi-agent-discussion) | Agent graph + router + orchestrator + persistence, ≥3 rounds | `week3_demo.py` |
| [Week 4](#week-4--analytics--hardening) | Opinion/agreement analytics (`src/metrics/`) + retrieval hardening | `tests/test_opinion.py`, `tests/test_agreement.py` |

---

## Table of Contents

- [Week 1 — RAG Pipeline](#week-1--rag-pipeline)
- [Week 2 — Core Agent](#week-2--core-agent)
- [Week 3 — Multi-Agent Discussion](#week-3--multi-agent-discussion)
- [Week 4 — Analytics + Hardening](#week-4--analytics--hardening)
- [Setup](#setup)
- [Running](#running)
- [Project Structure](#project-structure)
- [LLM Providers](#llm-providers)
- [Tests](#tests)
- [Data](#data)
- [Limitations & Next Steps](#limitations--next-steps)

---

## Week 1 — RAG Pipeline

**Goal:** build a grounded knowledge base from climate-finance sources and retrieve evidence with hybrid search.

### Stages

| Stage | File | How |
|-------|------|-----|
| Scrape | `scraper.py` | `crawl4ai`, ~122 IPCC/UNFCCC/IRENA/IEA/WRI/ILO URLs, 3s sleep, skip-if-exists → `data/raw/doc_<md5>.md` |
| Chunk | `chunker.py` | `RecursiveCharacterTextSplitter` 1000/200, skips source-only chunks → `data/chunks/master_chunks.json` |
| Embed | `embedder.py` | `all-MiniLM-L6-v2` (384-d) → Postgres `pgvector` + `BM25Okapi` → `bm25_index.pkl` (generated, gitignored) |
| Store | `setup_postgres.py` | Creates `vector` extension + `climate_docs(id, doc_id, source_url, chunk_text, embedding)` in DB `climate_rag` |
| Retrieve | `retriever.py` | `hybrid_search_with_metadata(query, top_k=30, rrf_k=60, final_k=3)`: BM25 + vector → RRF merge → `ms-marco-MiniLM-L-6-v2` cross-encoder re-rank. Lazy-loaded with graceful degradation (torch/Postgres optional — falls back to BM25 built from `master_chunks.json`; see Week 4) |
| Generate | `rag_agent.py` | Interactive CLI: retrieval + Gemini synthesis (temp 0.2) with citations |
| Evaluate | `evaluate_rag.py` | 5 ground-truth queries, Precision@3 ≈ 1.00, Recall ≈ 0.78 → `docs/evaluation.md` |

```bash
python setup_postgres.py
python scraper.py      # → data/raw/
python chunker.py      # → data/chunks/master_chunks.json
python embedder.py     # → pgvector + bm25_index.pkl
python rag_agent.py    # interactive grounded Q&A
python evaluate_rag.py # retrieval scores → docs/evaluation.md
```

---

## Week 2 — Core Agent

**Goal:** a reusable, persona-agnostic `Agent` that orchestrates persona + memory + tools + LLM generation — no hardcoded provider or persona.

### Architecture

```
Persona (JSON config)
     │
     ▼
┌─────────┐
│  Agent  │  src/agent.py — respond() + generate_opinion()
└────┬────┘
     ├── Memory (Protocol / Conversation / Hybrid)
     ├── Tools  (climate_knowledge_search, financial_calculator, web_search)
     └── LLM    (provider registry, auto-discovered from src/llm/*.py)
              │
              ▼
     Prompt builder (grounding rules → OPINION / EVIDENCE / REASONING / CAVEATS)
              │
              ▼
     Structured opinion {topic, persona, opinion, evidence, sources,
                         calculation, web_results, provider, model}
```

Tool routing is **keyword-based**: financial words (roi/npv/calculate/…) → `financial_calculator`; recency words (latest/recent/2026/…) → `web_search`; otherwise → `climate_knowledge_search` (Week 1 adapter).

### Agent API

```python
from src.agent import Agent
from src.personas import load_persona, list_personas
from src.llm import get_provider
from src.tools import RetrievalTool

print(list_personas())  # investor, policy_expert, scientist, ...

agent = Agent(persona=load_persona("investor"),
              llm=get_provider(),          # reads LLM_* env vars
              tools=[RetrievalTool()])

agent.respond("What is climate adaptation finance?")          # conversational
agent.generate_opinion("Should developed countries increase climate finance?")  # structured
agent.generate_opinion("Calculate ROI for a $1M solar farm",
                       calculation="roi", initial=1_000_000, final=1_400_000)
```

Add a tool by subclassing `src.tools.base.Tool` (`name`, `description`, `run() → ToolResult`).

### Personas

JSON in `personas/` (`{name, description, system_prompt, tone, focus_areas}`), auto-discovered via `load_persona(name)`:

| File | Role |
|------|------|
| `investor.json` | Climate Investor — ROI, risk, green bonds |
| `policy_expert.json` | Policy Expert — equity/CBDR, IPCC/UNFCCC/NDC, loss & damage |
| `scientist.json` | Environmental Scientist — carbon budgets, MRV, IPCC evidence |
| `cfo_agent.json` | CFO — NPV/IRR/payback, stranded assets |
| `env_specialist.json` | ESG analyst — anti-greenwashing, LCA, net-zero |
| `industry_representative.json` (+ typo duplicate `industry__represenatative.json`) | Renewables manager — LCOE, blended finance |
| `labour_representative.json` | ILO / just-transition |
| `Government Agent.json` / `Fossil Fuel Industry Agent.json` | Diplomatic phased-policy / bridge-fuel + CCS views |
| `sustainable_supply_chain.json` / `policy_compliance_officer.json` | Operational/compliance variants (used in evals) |

### Tools & memory (built in Week 2, extended later)

- `climate_knowledge_search` — Week 1 adapter, `[{source_url, chunk_text, rerank_score}]`.
- `financial_calculator` — pure-math `npv()` + `roi()`.
- `web_search` — `ddgs` + parallel fetch; HTML (`trafilatura/bs4`), PDFs (`pypdf` + `PyMuPDF+pytesseract` OCR), `[Page N]` chunking.
- `Memory` Protocol → `ConversationMemory` (bounded history) → `AgentMemory` (history + key-value facts). RAM-only (see `demo.py`).

```bash
python week2_demo.py --persona investor --topic "Should fossil fuel subsidies be eliminated?" -v
python week2_demo.py --provider openrouter   # override provider
```

Details: `docs/architecture.md`.

---

## Week 3 — Multi-Agent Discussion

**Goal:** a discussion engine — agents wired in a directed graph, routed deterministically, orchestrated over ≥3 rounds, with opinion tracking and persistent state.

```
AgentGraph (ring / fully-connected / persona_based_topology)
  │  BFS forward + transpose → strongly connected
  ▼
GraphRouter.get_next_recipients(agent_id) → neighbors only (recipient_id metadata)
  ▼
DiscussionOrchestrator.start_discussion(topic, agents, config)
  rounds → scheduler → context (20-msg bound + own prior opinion + retrieval)
       → respond → route → opinion-track → persist → terminate
  ▼
Persistence (InMemory / File: data/discussions/{discussion_id}.json)
```

- **Graph** (`src/graph/`): `AgentGraph` + `create_ring / fully_connected / persona_based_topology` (finance→regulator→ESG→industry→finance plus cross-links); `validation.py` connectivity check.
- **Router** (`src/routing/graph_router.py`): fan-out to neighbors only; rejects non-connected graphs.
- **Orchestrator** (`src/orchestration/`): shared contracts in `models.py` (`Message/RetrievalEvent/OpinionRecord/DiscussionConfig/DiscussionState/DiscussionResult`); `SequentialScheduler` (same order each round), `MaxRoundsTermination`, bounded `DiscussionContextBuilder`, safe wrappers around respond/route/persist.
- **Persistence** (`src/persistence/file_persistence.py`): one full-state JSON per discussion (`save/load/exists/list/delete`); `InMemoryPersistence` for tests/demos.
- **Demo** (`week3_demo.py`): 4 round-aware persona agents (investor, regulator, ESG, CFO) with per-round evolving positions, 3 rounds (~18 routed messages), opinion trajectory + persistence check.

```bash
python week3_demo.py
python -m pytest tests/test_integration.py -v   # 6 behaviors: graph, routing,
                                                 # ≥3 rounds, retrieval, persistence, opinions
```

Guide: `docs/week3_guide.md`.

---

## Week 4 — Analytics + Hardening

### A. Opinion + Agreement analytics (`src/metrics/`)

Consumed later as `calculate_opinion_change(history)` / `calculate_agreement(history)`, where `history` is a Week 3 `DiscussionState` or its `to_dict()` (e.g. from `data/discussions/*.json`). No Week 3 code modified, no new dependencies.

**Opinion trajectory** (`opinion.py`): Week 3 stores free-text opinions only, so stance is derived deterministically — support/oppose cue counts with 3-token negation flip (`stance = (P−N)/(P+N)`, no cues → 0.0), ×0.8 conditional dampening, range [-1, +1] (−1 = against, +1 = in favor). In-range numerics pass through (future-proofs a Week 3 stance field). Output per agent/round: `{agent_id, round, stance, change, status, n_cues, n_snapshots}` + summaries (initial/final, total/largest movement, direction up/down/flat/mixed). `change` only across consecutive valid rounds; missing → `missing`, bad values → `invalid`, duplicate snapshots → last wins. Never invents values.

**Agreement** (`agreement.py`): one score per round — `1 − mean(pairwise |Δstance|) / 2`, clamped [0, 1] (1 = full agreement, 0 = max disagreement). 0–1 valid stances → `insufficient_data` (never fake 1.0); invalid/missing excluded and counted.

```bash
python -m pytest tests/test_opinion.py tests/test_agreement.py -v  # 29 tests
```

Full method docs: `docs/opinion_agreement_metrics.md`.

### B. Retrieval hardening (fixes the reported `week2_demo` failure)

`retriever.py` used to load models + BM25 + Postgres **at import**, so one broken dep (the `PreTrainedModel` torch/transformers mismatch — not Postgres) killed all retrieval → "cannot formulate a grounded opinion". Now: lazy loading, clear per-cause error hints, BM25 fallback from `master_chunks.json` (no torch/DB needed), `RetrievalTool` auto-falls-back. `requirements.txt` documents the torch/transformers pair-upgrade fix.

### C. Demo & repo fixes

- `week3_demo.py`: `DemoAgent`s are round-aware (parse round/history from context, per-role 3-round arcs, evolving opinions); prints graph edges + routing metadata; fixed Windows cp1252 emoji crash.
- `personas/scientist.json` restored (tests + docs expect it); deleted committed 0-byte `labour__representative.json`; moved stray `import os` in `src/llm/base.py` to top.

### D. Multi-LLM benchmarking (scripts + reports)

- `test_glm53flash.py` → GLM-5.3-Flash × investor/policy_expert → `docs/glm53flash_test_report.md`.
- `test_personas_llms.py` / `simple_llm_test.py` → GPT-OSS-120B/20B via Groq → `docs/personas_llms_test_report.md`.
- `run_evaluation.py`, `run__evaluation.py`/`runevaluation.py` → scripted evals (DeepSeek/Nemotron) → `evaluation_results.json`, `test_results*.json`, `my_test_results.json`.

---

## Setup

```bash
git clone https://github.com/Omar-Elemary/climate-finance-ai-agent.git
cd climate-finance-ai-agent
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Knowledge base (Week 1; Postgres+pgvector only needed for vector search —
# BM25 fallback works without it)
python setup_postgres.py   # DB climate_rag / user postgres
python scraper.py          # → data/raw/
python chunker.py          # → data/chunks/master_chunks.json
python embedder.py         # → pgvector + bm25_index.pkl

# LLM keys (cp .env.example .env):
# LLM_PROVIDER=openrouter | openai | gemini | ollama | anthropic | openai_compat
# LLM_API_KEY=...  (or <PROVIDER>_API_KEY, e.g. GEMINI_API_KEY)
# LLM_MODEL=...  LLM_TEMPERATURE=0.2  LLM_MAX_TOKENS=2048
# NOTE: new Google AI Studio keys start with "AQ." — use LLM_PROVIDER=gemini
# (native google-genai route), not an OpenAI-compatible path.
```

Main deps: `crawl4ai, langchain-text-splitters, sentence-transformers, torch, torchvision, pgvector, psycopg2-binary, rank_bm25, python-dotenv, google-genai, openai>=1.0.0, pydantic>=2.0, pytest, pytest-mock`.

---

## Running

```bash
python rag_agent.py                                   # W1 interactive RAG
python week2_demo.py --persona investor --topic "..." # W2 multi-persona opinions
python week3_demo.py                                  # W3 4-agent × 3-round discussion
python demo.py                                        # memory fact-recall demo
python simple_llm_test.py                             # provider smoke test
python -m pytest tests/ -v                            # 103 tests
```

---

## Project Structure

```
├── scraper.py / chunker.py / embedder.py / setup_postgres.py / retriever.py  # W1
├── rag_agent.py / evaluate_rag.py                                            # W1 run + eval
├── week2_demo.py / week3_demo.py / demo.py                                   # W2 / W3 / memory demos
├── test_glm53flash.py / test_personas_llms.py / simple_llm_test.py           # W4 benchmarks
├── run_evaluation.py / run__evaluation.py / runevaluation.py
├── src/
│   ├── agent.py                 # W2 Agent
│   ├── llm/                     # base / openrouter / openai_compat / gemini (+ auto-discovery)
│   ├── tools/                   # base / retrieval / financial_calculator / web_search
│   ├── memory/                  # base / conversation / hybrid
│   ├── personas/                # base dataclass / loader
│   ├── prompts/builder.py       # context + opinion message builders
│   ├── graph/                   # W3 base / topology / validation
│   ├── routing/                 # W3 base / graph_router
│   ├── orchestration/           # W3 orchestrator / models / context / scheduler /
│   │                            #      termination / retriever / persistence / router
│   ├── persistence/             # W3 file_persistence (data/discussions/*.json) / models
│   └── metrics/                 # W4 opinion.py / agreement.py
├── personas/*.json              # 12 personas (investor, policy_expert, scientist, ...)
├── tests/                       # unit + test_integration + test_opinion + test_agreement + demo smokes
├── docs/                        # architecture / evaluation / week3_guide /
│                                #   opinion_agreement_metrics / glm + personas LLM reports
└── data/                        # raw/ chunks/master_chunks.json discussions/
```

---

## LLM Providers

Auto-discovered from `src/llm/*.py`; select with `LLM_PROVIDER`:

| Provider | Value | Default model |
|----------|-------|---------------|
| OpenRouter | `openrouter` | `anthropic/claude-3.5-sonnet` |
| OpenAI | `openai` | `gpt-4o-mini` |
| Gemini | `gemini` | `gemini-3.5-flash` |
| Ollama | `ollama` | `llama3.1` (local) |
| Anthropic | `anthropic` | `claude-3-5-sonnet-20241022` |
| Any OpenAI-compat | `openai_compat` | + `LLM_BASE_URL` |

Benchmarked here: GLM-5.3-Flash (OpenRouter), GPT-OSS-120B/20B (Groq), Gemini 3.5/3.7-flash, Nemotron super/ultra (OpenRouter).

---

## Tests

103 tests, no live LLM/DB needed: unit (agent/llm/tool/personas/prompts/memory/graph/orchestration/persistence), `test_integration.py` (6 W3 behaviors), `test_opinion.py` + `test_agreement.py` (29 W4 metric tests), demo smokes.

```bash
python -m pytest tests/ -v
```

---

## Data

- `data/raw/` — ~100 scraped `.md` docs with source headers.
- `data/chunks/master_chunks.json` — `{chunk_id, parent_doc_id, source_url, text}`.
- `data/discussions/` — persisted discussion states (e.g. `test-run-001.json`).
- `bm25_index.pkl` — generated by `embedder.py` (gitignored), optional at runtime.
- Root `*.json` — benchmark/eval result traces.

---

## Limitations & Next Steps

- Keyword (not LLM) tool routing — future: function-calling.
- Hybrid memory + `FilePersistence` are single-process (no locking, full-overwrite) — fine for demos.
- Lexicon stance is a proxy (sarcasm/diplomatic hedging compress toward 0); prefer a real Week 3 numeric stance if added.
- Duplicate eval scripts (`run__evaluation.py` ≈ `runevaluation.py`) and the `industry__represenatative.json` typo-duplicate remain — consolidate next.
- Out of this repo's scope (teammates'): influence, sentiment, reporting, visualization, unified engine, Week 5 frontend.

Per-week details: `docs/architecture.md` (W2) · `docs/week3_guide.md` (W3) · `docs/evaluation.md` (W1 scores) · `docs/opinion_agreement_metrics.md` (W4).
### Metric: Agent Influence

* **Purpose:**  
  Quantifies the estimated directional influence of each agent on the overall discussion by measuring how much other participants converge toward that agent's stance across consecutive rounds.

* **Input:**  
  Discussion history (either a `DiscussionState` instance or a raw `dict`) containing:
  * `opinions`: Round-by-round opinion snapshots per agent.
  * `messages`: Transcript of speaker contributions per round.

* **Formula / Methodology:**  
  Inspired by the DeGroot opinion dynamics and network convergence models:
  1. For each consecutive round transition ($r \to r+1$):
     * A speaker $A$ must have actively contributed in round $r$ (when message history is provided).
     * For every peer $B \neq A$, the convergence pull toward $A$ is calculated:
       $$\text{Pull}(A \to B, r) = |S_B(r) - S_A(r)| - |S_B(r+1) - S_A(r)|$$
       *(A positive value indicates that agent $B$ shifted closer to agent $A$'s stance).*
  2. Aggregated pull scores are floored at $0.0$ to focus on positive attraction/alignment.
  3. The final score is normalized across all agents such that:
     $$\sum_{i=1}^{N} \text{InfluenceScore}_i = 1.0$$

* **Output:**  
  A mapping of `agent_id` to an `AgentInfluence` object containing:
  * `influence_score`: Normalized value in $[0.0, 1.0]$ (or `None` if data is insufficient).
  * `raw_pull`: Absolute mean convergence pull.
  * `messages_sent`: Total message count recorded for the agent.
  * `status`: `"ok"` or `"insufficient_data"`.

* **Interpretation:**  
  * **Higher Score:** Indicates that shifts in other agents' stances were strongly correlated with and moved toward this agent's expressed position.
  * **Important Distinction:** This metric reflects statistical association and convergence correlation over network transitions; it does not claim direct psychological or causal persuasion.

* **Edge Cases & Limitations:**  
  * **$< 2$ Agents or $< 2$ Rounds:** Returns `None` with status `"insufficient_data"`.
  * **Static Opinions (Zero Movement):** Returns `0.0` for all agents with status `"ok"` (no fabricated scores).
  * **Missing / Corrupted Stances:** Invalid stance values are safely filtered out using `opinion.extract_stance` validation.
  