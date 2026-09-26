# API Contract — Qubeterra Climate Finance API (Persona 3, Week 5)

> Frontend developers: build against this document. You do not need to read
> backend implementation code, RAG internals, routing, prompts, persistence,
> or Week 4 metric math.

Base URL (local): `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs` (OpenAPI/Swagger UI)

All responses are JSON. Errors share one shape:

```json
{ "error": { "code": "DISCUSSION_NOT_FOUND", "message": "Discussion 'x' was not found." } }
```

| HTTP | Meaning | `error.code` |
|------|---------|--------------|
| 200/201 | success | — |
| 400 | invalid request (service-level, e.g. unknown persona) | `INVALID_REQUEST` |
| 404 | unknown discussion id (incl. `/analytics`) | `DISCUSSION_NOT_FOUND` |
| 422 | schema validation failed | `VALIDATION_ERROR` |
| 503 | LLM / retrieval / analytics dependency unavailable | `SERVICE_UNAVAILABLE` / `ANALYTICS_UNAVAILABLE` |
| 500 | unexpected | `INTERNAL_ERROR` |

---

## `GET /health`

```json
{ "status": "ok" }
```

## `GET /topics`

Returns curated climate-finance topics. Each item:

```json
[
  {
    "id": "industrial-decarbonization",
    "title": "Financing Industrial Decarbonization and Green Hydrogen",
    "domain": "mitigation",
    "description": "...",
    "suggested_personas": ["investor", "policy_expert", "env_specialist", "cfo_agent"]
  }
]
```

## `POST /discussions` → `202`

Launches a **real** discussion in the background and returns a `RUNNING`
skeleton immediately (`discussion_id`, `topic`, `participants`,
`rounds_completed: 0`, `status: "running"`, empty `rounds[]`/`messages[]`).
The debate then streams into persistence turn by turn.

Request (all fields match the Core Agent contract: `topic` + `DiscussionConfig`):

```json
{
  "topic": "Financing Industrial Decarbonization and Green Hydrogen",
  "domain": "mitigation",
  "num_rounds": 3,
  "personas": ["investor", "policy_expert", "scientist"],
  "enable_retrieval": true
}
```

- `topic` (required, non-empty), `domain` (optional grouping tag — API-level only, not stored in Week 3 state), `num_rounds` 1–10 (default 3), `personas` (optional; defaults to investor/policy_expert/scientist; names must exist in `personas/*.json`), `enable_retrieval` (default true; agents use the Week 1 tool, orchestrator-level retriever stays off as in `week3_demo.py`).

Response (`DiscussionResponse`): `discussion_id`, `topic`, `domain`, `participants`, `rounds_completed`, `total_rounds`, `status`, `rounds[]` (messages grouped by round), `messages[]`, `opinions{agent: [...]}`, `started_at`, `completed_at`, `error`, `conclusion` (3-bullet closing synthesis; present once `status` is `completed`, `null` while `running`).

Poll `GET /discussions/{id}` every ~3s until `status` is `completed` (or
`failed`): each poll returns more `rounds[]`/`messages[]` as turns land.
Terminal states are `completed` / `failed`; without
`LLM_PROVIDER`/`LLM_API_KEY`, launch itself returns `503 SERVICE_UNAVAILABLE`
with a fix hint.

## `GET /discussions/{discussion_id}` → `200`

Same `DiscussionResponse` shape, loaded from the Core persistence (`FilePersistence`, `data/discussions/<id>.json`). Unknown id → `404 DISCUSSION_NOT_FOUND`.

## `GET /discussions/{discussion_id}/analytics` → `200`

Calls Week 4 through `src.analytics.run_analytics(state)` — no metric math lives in the backend. Returns:

```json
{
  "discussion_id": "...",
  "topic": "...",
  "generated_at": "...",
  "schema_version": "1.0",
  "summary": { "n_agents": 3, "n_rounds": 2, "...": "..." },
  "opinion_trajectory": { "investor": [{ "round": 1, "stance": 1.0, "change": null, "status": "ok" }] },
  "agreement": [{ "round": 1, "agreement_score": 0.5, "status": "ok" }],
  "influence": { "investor": { "influence_score": 0.4, "messages_sent": 2, "status": "ok" } },
  "sentiment": [],
  "interaction_graph": {
    "nodes": [{ "agent_id": "investor", "message_count": 2, "influence_score": 0.4 }],
    "edges": [{ "source": "investor", "target": "policy_expert", "weight": 2.0, "kind": "message" }]
  },
  "metric_statuses": { "opinion": { "status": "ok" }, "sentiment": { "status": "unavailable" } },
  "warnings": []
}
```

Notes:

- `opinion_trajectory` / `agreement` / `influence` are direct adaptations of Week 4 output (deterministic, no LLM).
- `sentiment` is `[]` with `metric_statuses.sentiment.status == "unavailable"` in this repo state: `src/metrics/sentiment.py` exposes only run-id-based helpers, so the unified engine has no matching entry point. The backend surfaces this honestly instead of synthesizing scores. If Persona 4 adds `calculate_sentiment(history)`, it lights up with no backend change.
- `interaction_graph` is a backend derivation (not a Week 4 metric): nodes from participants + message counts + influence scores; edges from `GraphRouter` `recipient_id` metadata, falling back to co-participation weights when metadata is absent.

---

## Frontend flow

1. `GET /topics` → populate picker.
2. `POST /discussions` → get `discussion_id` in milliseconds, navigate at once.
3. `GET /discussions/{id}` → poll while `status == "running"`; render rounds/messages/opinions as they stream.
4. `GET /discussions/{id}/analytics` → render dashboard once `completed` (trajectory chart, agreement, influence, sentiment, graph).
