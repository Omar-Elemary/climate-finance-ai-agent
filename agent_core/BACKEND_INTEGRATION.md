# Backend integration note — switching Persona 3's temporary logic to `agent_core`

> Owned by Persona 1. Lives here (not in `backend/`) because Persona 1 MUST NOT
> modify `backend/`. When Persona 3 is ready, they apply this diff themselves.

## Current state (working, untouched)

`backend/app/services/discussion_service.py` currently reaches `src.*` directly
(`load_persona`, `Agent(get_provider() + RetrievalTool)`, persona-based graph,
`DiscussionOrchestrator`, `FilePersistence`) plus a `domain` sidecar. That file
is **not modified** by Persona 1 — it keeps working as-is.

## Known issue found (Persona 3 action, their file)

`backend/app/services/discussion_service.py::_agent_id_for_persona` reads
`.name` off the **agent** (`getattr(persona, "name", ...)` called with an
`Agent`), but Week 2 `Agent` objects carry the name on `agent.persona.name`.
The helper therefore returns `repr(agent)` (`<src.agent.Agent object ...>`),
so the persona graph nodes never match the orchestrator's sender ids, the
`GraphRouter` silently falls back to passthrough, and `metadata.recipient_id`
is lost on every message (the analytics interaction-graph fallback masks it).

Recommended one-line fix on their side (mirrors
`DiscussionOrchestrator._get_agent_id`; already implemented correctly in
`agent_core/service.py::agent_id_for_persona`):

```python
persona = getattr(agent, "persona", None)
name = getattr(persona, "name", None) or getattr(agent, "name", None) or str(agent)
return str(name).lower().replace(" ", "_")
```

Evidence: with the buggy derivation a 3-agent/1-round run yields 3 messages
with `metadata == {}`; with the fix the same run yields routed copies carrying
`metadata.recipient_id` (see `test_metadata_preserved_agent_round_recipient_retrieval`).

## Target: consume `agent_core` (drop-in)

`agent_core` exposes exactly the `REQUIRED_CORE_INTERFACE` documented in that
file, with Core-level errors instead of backend errors:

```python
from agent_core import CoreDiscussionService, DiscussionRequest
from agent_core.exceptions import (
    AgentExecutionError,
    DiscussionExecutionError,
    DiscussionNotFound,
    InvalidDiscussionRequest,
)

core = CoreDiscussionService(persistence=<existing FilePersistence>)
state = core.create_discussion(DiscussionRequest(
    topic=body.topic,
    domain=body.domain,          # accepted, ignored at execution (API-only tag)
    num_rounds=body.num_rounds,  # 1..10, same as backend MAX_ROUNDS
    personas=body.personas,      # None -> investor/policy_expert/scientist
    enable_retrieval=body.enable_retrieval,
))
state = core.get_discussion(discussion_id)
state.to_dict()  # identical shape the backend already adapts
```

Behavioral parity (verified by tests on both sides):

- Same defaults (`investor/policy_expert/scientist`), same 1–10 clamp,
  same `persona.name.lower().replace(" ", "_")` id derivation (graph ids stay
  aligned with the orchestrator), same `create_persona_based_topology` +
  `GraphRouter` (so `metadata.recipient_id` survives for the analytics
  interaction graph), same `DiscussionConfig` mapping, same
  `FilePersistence(data/discussions)` default, same POST-then-reload so
  POST and GET share one source, same Week 4 compatibility
  (`src.analytics.run_analytics(state)`).

## Minimal Persona 3 diff (their call, their file)

1. In `backend/app/services/discussion_service.py`, replace the `src.*`
   orchestration block with the snippet above (or delegate the whole
   `DiscussionService` to `CoreDiscussionService`).
2. Map Core errors to the existing HTTP contract (no new codes):
   `InvalidDiscussionRequest` → 400, `DiscussionNotFound` → 404,
   `AgentExecutionError`/`DiscussionExecutionError` (incl. LLM-down) → 503,
   unexpected → 500.
3. Keep the `domain` sidecar and `_adapt_state` exactly as they are —
   `agent_core` intentionally does not own `domain`.

## Field contract (backend expectations, all preserved)

`state.to_dict()` → `discussion_id, topic, participants, messages[]`
(`message_id/agent_id/agent_name/round/content/timestamp/metadata.recipient_id`),
`opinions{agent: [{agent_id/agent_name/round/opinion/evidence/sources}]}`,
`retrieval_events[]` (Week 1 context), `status, current_round, total_rounds,
started_at, completed_at, error`. Views in `agent_core/schemas.py`
(`agents_view/rounds_view/messages_view/retrieval_context_view`) derive the
`agents/rounds/messages/retrieval_context` projections without inventing data.
