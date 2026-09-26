"""Core discussion service — the stable integration boundary (Persona 1).

Backend usage (conceptual — see agent_core/BACKEND_INTEGRATION.md)::

    from agent_core import CoreDiscussionService, DiscussionRequest

    core = CoreDiscussionService()  # FilePersistence, real Agents
    state = core.create_discussion(DiscussionRequest(topic="...", num_rounds=3))
    state = core.get_discussion(discussion_id)
    state.to_dict()  # -> backend schemas -> JSON

Real execution flow (nothing faked, nothing reimplemented)::

    DiscussionRequest
      -> validate -> load_personas (src.personas)
      -> create_agents (src.agent.Agent + src.llm.get_provider + Week 1 RetrievalTool)
      -> persona graph (src.graph.AgentGraph.create_persona_based_topology)
      -> GraphRouter (src.routing) — recipient_id metadata preserved
      -> DiscussionOrchestrator.start_discussion (src.orchestration, Week 3)
           -> Agent.respond() per turn + generate_opinion() per round
           -> Week 1 RAG flows INSIDE agents via RetrievalTool
               (retriever.hybrid_search_with_metadata, BM25 fallback)
      -> persisted DiscussionState (src.persistence.FilePersistence)
      -> return re-loaded state (single source for GET + Week 4 analytics)

The service never touches prompts, routing math, RAG internals, metric math,
or HTTP. LLM is the only external dependency; tests inject ``agent_factory``
(or a fake ``llm_provider_factory``) so no paid calls are needed.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from agent_core.exceptions import (
    AgentExecutionError,
    DiscussionExecutionError,
    DiscussionNotFound,
    InvalidDiscussionRequest,
    RetrievalError,
)
from agent_core.schemas import (
    DEFAULT_PERSONAS,
    DiscussionRequest,
    DiscussionState,
)

logger = logging.getLogger(__name__)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_storage_dir() -> Path:
    return _repo_root() / "data" / "discussions"


def agent_id_for_persona(agent: Any) -> str:
    """Derive the routing id for an agent.

    Mirrors ``DiscussionOrchestrator._get_agent_id`` exactly: Week 2 Agents
    (and test doubles) carry the name on ``agent.persona.name``, NOT on the
    agent itself. Reading ``agent.name`` directly yields ``repr(agent)``,
    which silently disconnects the graph (router falls back to passthrough
    and ``recipient_id`` metadata is lost).
    """
    persona = getattr(agent, "persona", None)
    name = getattr(persona, "name", None)
    if name is None:
        name = getattr(agent, "name", None)
    if name is None:
        name = str(agent)
    return str(name).lower().replace(" ", "_")


class CoreDiscussionService:
    """Production-ready Core Agent layer around Week 1 + Week 3."""

    def __init__(
        self,
        persistence: Any | None = None,
        storage_dir: str | Path | None = None,
        agent_factory: Callable[[Any], Any] | None = None,
        llm_provider_factory: Callable[[], Any] | None = None,
    ) -> None:
        if persistence is not None:
            self.persistence = persistence
        else:
            from src.persistence import FilePersistence

            self.persistence = FilePersistence(
                storage_dir=str(storage_dir or _default_storage_dir())
            )
        self._agent_factory = agent_factory
        self._llm_provider_factory = llm_provider_factory

    # ------------------------------------------------------------------ public

    def create_discussion(self, request: DiscussionRequest) -> DiscussionState:
        """Execute a REAL Week 1 + Week 3 discussion. No fake messages."""
        if not isinstance(request, DiscussionRequest):
            raise InvalidDiscussionRequest(
                f"request must be DiscussionRequest, got {type(request).__name__}."
            )
        try:
            req = request.validated()
        except InvalidDiscussionRequest:
            raise
        except Exception as exc:
            raise InvalidDiscussionRequest(f"Invalid request: {exc}") from exc

        personas = self._load_personas(req.personas or list(DEFAULT_PERSONAS))
        agents = [self._build_agent(p) for p in personas]
        agent_ids = [agent_id_for_persona(a) for a in agents]

        graph = self._build_graph(agent_ids)
        config = req.to_config()
        orchestrator = self._build_orchestrator(graph)

        try:
            result = orchestrator.start_discussion(topic=req.topic, agents=agents, config=config)
        except (InvalidDiscussionRequest, DiscussionNotFound):
            raise
        except Exception as exc:
            logger.exception("Core discussion execution failed")
            raise DiscussionExecutionError(f"Core discussion failed: {exc}") from exc

        state = self._as_state(result)
        if self._status_of(state) == "failed":
            raise DiscussionExecutionError(
                f"Core discussion failed: {getattr(state, 'error', 'unknown error')}"
            )

        # Single source of truth: return the persisted state so GET, analytics
        # (src.analytics.run_analytics) and this return value agree exactly.
        try:
            reloaded = self.persistence.load(state.discussion_id)
        except Exception as exc:
            raise DiscussionExecutionError(
                f"Discussion store unavailable after run: {exc}"
            ) from exc
        if reloaded is None:
            raise DiscussionExecutionError(
                "Discussion was not persisted after run; cannot return a stable id."
            )
        return reloaded

    def get_discussion(self, discussion_id: str) -> DiscussionState:
        discussion_id = (discussion_id or "").strip()
        if not discussion_id:
            raise InvalidDiscussionRequest("discussion_id must be a non-empty string.")
        try:
            state = self.persistence.load(discussion_id)
        except Exception as exc:
            logger.exception("Core persistence load failed")
            raise DiscussionExecutionError(
                f"Discussion store unavailable: {exc}"
            ) from exc
        if state is None:
            raise DiscussionNotFound(discussion_id)
        return state

    def list_discussions(self) -> list[str]:
        """Best-effort id listing; [] when the backend lacks enumeration."""
        for attr in ("list_discussion_ids", "list_ids", "list"):
            candidate = getattr(self.persistence, attr, None)
            if callable(candidate):
                try:
                    ids = candidate()
                    return [str(i) for i in ids or []]
                except Exception as exc:
                    raise DiscussionExecutionError(
                        f"Could not list discussions: {exc}"
                    ) from exc
        return []

    # ------------------------------------------------------------- internals
    # Each helper consumes exactly one public subsystem — no deep internals.

    def _load_personas(self, names: list[str]) -> list[Any]:
        try:
            from src.personas import list_personas, load_persona
        except Exception as exc:
            raise DiscussionExecutionError(
                f"Persona subsystem unavailable: {exc}"
            ) from exc
        try:
            available = set(list_personas())
        except Exception:
            available = set()
        unknown = [n for n in names if available and n not in available]
        if unknown:
            raise InvalidDiscussionRequest(
                f"Unknown persona(s): {', '.join(unknown)}. "
                f"Available: {', '.join(sorted(available))}"
            )
        loaded = []
        for name in names:
            try:
                loaded.append(load_persona(name))
            except FileNotFoundError as exc:
                raise InvalidDiscussionRequest(str(exc)) from exc
            except Exception as exc:
                raise DiscussionExecutionError(
                    f"Failed to load persona '{name}': {exc}"
                ) from exc
        return loaded

    def _build_agent(self, persona: Any) -> Any:
        if self._agent_factory is not None:
            try:
                return self._agent_factory(persona)
            except (InvalidDiscussionRequest, DiscussionNotFound):
                raise
            except Exception as exc:
                raise AgentExecutionError(
                    f"Custom agent factory failed for '{getattr(persona, 'name', persona)}': {exc}"
                ) from exc
        try:
            from src.agent import Agent
            from src.tools import RetrievalTool
        except Exception as exc:
            raise AgentExecutionError(f"Core agent subsystem unavailable: {exc}") from exc
        llm = self._resolve_llm()
        try:
            # Week 1 RAG attaches HERE: the agent's generate_opinion() routes
            # to RetrievalTool -> retriever.hybrid_search_with_metadata
            # (with BM25-only fallback). No second RAG system exists.
            return Agent(persona=persona, llm=llm, tools=[RetrievalTool()])
        except Exception as exc:
            raise AgentExecutionError(f"Failed to build agent: {exc}") from exc

    def _resolve_llm(self) -> Any:
        if self._llm_provider_factory is not None:
            try:
                return self._llm_provider_factory()
            except Exception as exc:
                raise AgentExecutionError(f"LLM provider failed: {exc}") from exc
        try:
            from src.llm import get_provider

            return get_provider()
        except ValueError as exc:
            raise AgentExecutionError(
                "LLM provider unavailable (missing API key or unknown provider). "
                f"Set LLM_PROVIDER/LLM_API_KEY. Detail: {exc}"
            ) from exc
        except Exception as exc:
            raise AgentExecutionError(f"LLM provider failed: {exc}") from exc

    def _build_graph(self, agent_ids: list[str]) -> Any:
        try:
            from src.graph.topology import AgentGraph
        except Exception as exc:
            raise DiscussionExecutionError(
                f"Graph subsystem unavailable: {exc}"
            ) from exc
        try:
            graph = AgentGraph.create_persona_based_topology(agent_ids)
        except Exception as exc:
            raise DiscussionExecutionError(f"Failed to build discussion graph: {exc}") from exc
        try:
            connected = graph.is_strongly_connected()
        except Exception as exc:
            raise DiscussionExecutionError(f"Graph check failed: {exc}") from exc
        if not connected:
            raise DiscussionExecutionError(
                "Discussion graph is not strongly connected."
            )
        return graph

    def _build_orchestrator(self, graph: Any) -> Any:
        try:
            from src.routing.graph_router import GraphRouter
            from src.orchestration import DiscussionOrchestrator
        except Exception as exc:
            raise DiscussionExecutionError(
                f"Orchestrator subsystem unavailable: {exc}"
            ) from exc
        try:
            # Orchestrator-level retriever stays None (as in week3_demo.py):
            # retrieval flows through each Agent's RetrievalTool so evidence
            # lands in opinions (evidence/sources) for Week 4 + citations.
            return DiscussionOrchestrator(
                router=GraphRouter(graph), persistence=self.persistence
            )
        except Exception as exc:
            raise DiscussionExecutionError(
                f"Failed to initialize discussion engine: {exc}"
            ) from exc

    @staticmethod
    def _as_state(result: Any) -> DiscussionState:
        if isinstance(result, DiscussionState):
            return result
        from_state = getattr(result, "discussion_id", None)
        if from_state is not None:
            return result  # DiscussionResult — duck-typed; reloaded below
        raise DiscussionExecutionError(
            f"Unexpected engine result type: {type(result).__name__}"
        )

    @staticmethod
    def _status_of(state: Any) -> str:
        status = getattr(state, "status", "")
        return str(getattr(status, "value", status))


def check_retrieval_available() -> None:
    """Pre-flight for Week 1 RAG; raises RetrievalError with a fix hint."""
    try:
        from retriever import CHUNKS_PATH  # type: ignore[import-not-found]
    except Exception as exc:
        raise RetrievalError(f"Week 1 retriever not importable: {exc}") from exc
    if not CHUNKS_PATH.exists():
        raise RetrievalError(
            f"Chunk corpus not found at {CHUNKS_PATH}. "
            "Run scraper.py -> chunker.py first."
        )
