# Week 3 Multi-Agent Discussion Architecture Guide

## Overview
Week 3 focuses on enabling structured, multi-turn discussions among domain personas in Climate Finance using a strongly connected communication graph, deterministic routing, and state persistence.

## Key Components
1. **Agent Graph (`src/graph/`)**: Implements directed topologies (`AgentGraph`) guaranteeing strong connectivity (`is_strongly_connected`). Supports ring, fully connected, and persona-driven topologies.
2. **Graph Router (`src/routing/`)**: Directs message delivery based on neighbors defined by graph edges (`GraphRouter`), eliminating arbitrary message broadcasting.
3. **Orchestrator (`src/orchestration/`)**: Coordinates discussion execution over $\ge 3$ rounds, tracks message history, and logs retrieval events.
4. **Persistence Layer (`src/orchestration/persistence.py`)**: Implements state checkpoints (`save` and `load`) for auditability and session reconstruction.

---

## Testing Requirements & Verification

The test suite in `tests/test_integration.py` rigorously validates the 6 core system behaviors:

* **Graph Test**: Asserts that active topologies satisfy strong connectivity using cycle checks and graph traversal.
* **Routing Test**: Ensures `GraphRouter` delivers messages strictly to graph-defined neighbors and rejects malformed graphs.
* **Multi-round Test**: Executes an end-to-end discussion ensuring at least three full conversational rounds complete successfully.
* **Retrieval Test**: Verifies that active agents query and incorporate evidence from the Week 1 RAG retrieval system during deliberation.
* **Persistence Test**: Tests round-trip serialization by persisting a `DiscussionState` snapshot and reconstructing it without data loss.
* **Opinion Tracking Test**: Audits `OpinionRecord` updates per agent across successive discussion rounds.

---

## Running Tests

To run the complete test suite:
```bash
python -m pytest tests/ -v
