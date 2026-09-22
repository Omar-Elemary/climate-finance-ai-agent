# Backend/API — Persona 3 (Week 5)

Clean FastAPI boundary over the Week 1–4 core. Owns **only** `backend/`.

```
Frontend → FastAPI (backend/app) → DiscussionService → agent_core (src.*: Week 1+2+3)
                                 → AnalyticsService → Week 4 (src.analytics.run_analytics)
```

## Run

```bash
cd climate-finance-ai-agent
pip install -r backend/requirements.txt  # fastapi, uvicorn, httpx, pytest
cp .env.example .env  # set LLM_PROVIDER + LLM_API_KEY (else POST returns 503, honestly)
uvicorn backend.app.main:app --reload --port 8000
# docs: http://localhost:8000/docs
```

## Layout

```
backend/
├── app/
│   ├── main.py            # create_app(), routers, error handlers, OpenAPI meta
│   ├── routes/            # health | topics | discussions | analytics (thin)
│   ├── schemas/           # Pydantic contracts (internal models never leak)
│   ├── services/          # discussion_service (core) / analytics_service (W4 adapter) / topics_service
│   ├── core/              # curated TOPICS config + error model
│   └── dependencies/      # injectable singletons (overridable in tests)
├── tests/                 # API tests with stub agents — no LLM/network
├── API_CONTRACT.md        # frontend-facing contract
└── requirements.txt
```

## Rules respected

- Routes never touch LLM/RAG/agents/prompts — only `DiscussionService` / `AnalyticsService`.
- Week 4 algorithms never reimplemented — `AnalyticsService` calls `src.analytics.run_analytics` and adapts.
- `domain` is API-level grouping (sidecar `_backend_domains.json`); Week 3 models untouched.
- Errors never leak stack traces: `{error: {code, message, details?}}`.
- Tests: `python -m pytest backend/tests -v` (stub `respond`/`generate_opinion`, real `DiscussionOrchestrator` + real Week 4 engine).

## Endpoints

`GET /health` · `GET /topics` · `POST /discussions` · `GET /discussions/{id}` · `GET /discussions/{id}/analytics` — see `API_CONTRACT.md`.
