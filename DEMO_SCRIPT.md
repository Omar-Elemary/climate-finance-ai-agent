# QUBETERRA — Full Demo Script (recorded walkthrough)

**Total runtime:** ~12–14 minutes (plus 20s intro video).
**Flow:** intro video → idea (1 min) → code tour Weeks 1–4 (5 min) → LIVE war-room (5–6 min) → tests + close (1 min).

> Legend: **SAY** = speak this (paraphrase freely). **DO** = on-screen action.
> Keep the backend (`:8000`) and frontend (`:5173`) running before you hit record.

---

## 0. Setup checklist (before recording)

- [ ] Backend up: `http://127.0.0.1:8000/health` → `{"status":"ok"}`
- [ ] Frontend up: `http://localhost:5173/index.html` → 200
- [ ] Intro video ready: `brag-output-2026-09-27-175958/brag.mp4`
- [ ] Editor open at repo root; terminal open at repo root
- [ ] Backup discussion bookmarked (if the live debate stalls):
  `http://localhost:5173/discussion/39097768-b43f-46f1-b975-281d1feb5cea`
  (completed, 2 rounds, Industrial Decarbonization)
- [ ] Use **2 rounds** for the live run (fast: ~6 LLM calls on Groq `gpt-oss-20b`)

---

## 1. Intro — play the video (0:00–0:20)

**DO:** Play `brag-output-2026-09-27-175958/brag.mp4` fullscreen, then cut to yourself.

**SAY:** *"That was Qubeterra — our climate-finance AI war-room. In the next twelve minutes I'll show you the whole system: grounded retrieval, persona agents, live multi-agent debates, analytics — and then we'll run one live."*

---

## 2. The idea — 1 minute (0:20–1:20)

**DO:** Show `README.md` top table + `frontend` home page side by side.

**SAY:** *"Climate-finance questions don't have one right answer — an investor, a policy expert and a scientist will fight about them. So instead of one chatbot answer, we built a system where agents argue on the record. You table one hard motion, seat the agents, they debate with retrieved IPCC, UNFCCC, IRENA evidence, and you read the clash plus the analytics. Four builds stacked week by week: RAG retrieval, a reusable Agent, multi-agent discussion, analytics — topped with a FastAPI backend and this war-room frontend."*

---

## 3. Week 1 — RAG pipeline (1:20–3:00)

**DO:** Open `scraper.py` → `chunker.py` → `retriever.py` (scroll, don't read). Show `data/chunks/master_chunks.json` exists.

**SAY:** *"Week 1 is the knowledge base. We scraped ~122 IPCC, UNFCCC, IRENA, IEA and WRI sources, chunked them, embedded with MiniLM into Postgres pgvector plus a BM25 index. Retrieval is hybrid — BM25 plus vector merged with RRF, re-ranked with a cross-encoder — and it degrades gracefully to BM25-only without torch or Postgres. Ground-truth evaluation hit Precision@3 ≈ 1.00. Every agentúlater uses this as its evidence tool, so no claim in a debate is ungrounded."*

**DO (optional, 20s):** `Get-Content docs/evaluation.md | Select-Object -First 15` or just show the file.

---

## 4. Week 2 — Core Agent (3:00–4:30)

**DO:** Open `personas/investor.json`, then `src/agent.py` (class header), then `src/llm/__init__.py` (`get_provider`).

**SAY:** *"Week 2 is one reusable, persona-agnostic Agent: persona plus memory plus tools plus LLM. Personas are plain JSON — here the investor. The LLM layer is provider-agnostic: OpenRouter, OpenAI, Gemini, Ollama, or OpenAI-compatible — which is how we run Groq's gpt-oss-20b for the live debates. Same agent class, any persona, any provider. `week2_demo.py` is the runnable proof."*

---

## 5. Week 3 — Multi-agent discussion (4:30–6:00)

**DO:** Open `src/orchestration/` file list → `src/graph/topology.py` (one screen) → `run_live_debate.py` header (4-round real-LLM CLI debate).

**SAY:** *"Week 3 wires agents into a debate: a persona-based graph topology, a router deciding who speaks next, an orchestrator running the rounds, and file persistence so every turn survives restarts. `run_live_debate.py` runs a full 4-round debate on real LLMs with stance tracking and a final conclusion synthesis. The backend you're about to see live is a thin HTTP skin over exactly this core — routes never touch LLM or RAG code."*

---

## 6. Week 4 — Analytics (6:00–7:00)

**DO:** Open `src/analytics/` list + `tests/test_analytics_engine.py` (one screen). Mention honestly:

**SAY:** *"Week 4 measures the fight, deterministically, no LLM: opinion trajectory per agent per round, agreement scores, influence, and an interaction graph. One honest caveat our API contract documents: sentiment is majikku — the metric module only exposes run-id helpers, so the backend reports sentiment as unavailable instead of inventing scores. You'll see the rest as live charts in a minute."*

---

## 7. LIVE — Backend API (7:00–8:00)

**DO:** Open `http://127.0.0.1:8000/docs`. Expand `GET /health` → Try it → Execute (200). Then `GET /topics` → Execute — point at the 6 curated topics.

**SAY:** *"Week 5 is the stable boundary the frontend builds on. Health, topics, launch a discussion, poll it, analytics. Watch the key design: POST /discussions returns 202 with a RUNNING skeleton in milliseconds, and the debate streams into persistence turn by turn — the frontend polls every 3 seconds. Launch never blocks."*

**DO:** In Swagger, `POST /discussions` with:
```json
{"topic": "Should fossil fuel subsidies be eliminated?", "num_rounds": 2}
```
Execute → point at `discussion_id`, `"status": "running"`. **Copy the id.**

---

## 8. LIVE — War-room frontend (8:00–11:30) ⭐ centerpiece

**DO:** Open `http://localhost:5173/` → pick the topic **"Should fossil fuel subsidies be eliminated?"**, personas investor + policy_expert + scientist, rounds **2**, retrieval ON → Start.

**SAY:** *"Table the motion. Pick the agents. They argue on record — I read the clash, not a summary."* (verbatim tagline from the app)

**DO:** Land on `/discussion/:id`. Point out: LIVE status, round replay at 2x, message cards with agent colors, ROUND stamps, the ticker *"IPCC · UNFCCC · IRENA · IEA /// DISAGREEMENT IS DATA"*.
**SAY while it streams:** *"Each turn is a real Groq call with retrieved evidence. The backend persists every turn, so this page is just polling — refresh-safe."*

**DO:** When `completed`: scroll to the **conclusion** (3-bullet closing synthesis) → click through to `/discussion/:id/analytics`.
**SAY:** *"And the after-action: opinion trajectories round by round, agreement score, influence per agent, interaction graph. Disagreement is data — literally charted."*

> ⚠️ **If the live run stalls (>3 min, or a 503):** say *"Live LLMs are moody — here's one from earlier,"* and open the backup:
> `http://localhost:5173/discussion/39097768-b43f-46f1-b975-281d1feb5cea` → its analytics page. Continue as normal.

---

## 9. Tests + close (11:30–12:30)

**DO:** Terminal: `python -m pytest backend/tests -q` → **11 passed**.

**SAY:** *"Eleven backend API tests with stub agents — real orchestrator, no LLM, no network — plus 59 analytics tests, frontend typecheck clean. That's Qubeterra: grounded retrieval, persona agents, live debates on the record, and analytics over the fight. Thanks — questions?"*

---

## Appendix — Q&A cheat sheet

| Question | Answer |
|---|---|
| Which LLM? | Provider-agnostic; demo runs Groq `openai/gpt-oss-20b` via `openai_compat`. Swap with env vars. |
| Why 202 + polling? | Debates take minutes; POST returns a RUNNING skeleton in ms, turns stream into `data/discussions/<id>.json`. |
| Where is state? | `FilePersistence` JSON per discussion + `_backend_domains.json` sidecar for the API-level `domain` tag. |
| What if no API key? | POST returns `503 SERVICE_UNAVAILABLE` with a fix hint — honest errors, never stack traces. |
| Sentiment empty? | Known gap, documented in `API_CONTRACT.md`; lights up when `calculate_sentiment(history)` exists. No backend change needed. |
| How many personas? | 12 JSON personas (`personas/`); defaults investor / policy_expert / scientist; 1–10 rounds. |
