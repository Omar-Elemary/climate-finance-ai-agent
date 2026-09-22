"""Discussion service — the ONLY place that talks to the Core Agent.

Route layer must stay thin::

    API route -> DiscussionService -> Core public interface

Consumed public interfaces (never internals):
  - src.personas.load_persona / list_personas
  - src.llm.get_provider
  - src.agent.Agent
  - src.tools.RetrievalTool
  - src.graph.topology.AgentGraph.create_persona_based_topology
  - src.routing.graph_router.GraphRouter
  - src.orchestration.DiscussionOrchestrator / DiscussionConfig
  - src.orchestration.InMemoryPersistence + src.persistence.FilePersistence

If Persona 1 ever extracts this into `agent_core/`, only this file (plus the
REQUIRED_CORE_INTERFACE note below) needs to change — routes stay untouched.

REQUIRED_CORE_INTERFACE (for Persona 1, if they formalize agent_core/):
    discussion_service.create_discussion(request) -> DiscussionState
    discussion_service.get_discussion(discussion_id) -> DiscussionState
  where request carries {topic, domain?, num_rounds, personas?, enable_retrieval}
  and the state exposes .to_dict() with {discussion_id, topic, participants,
  messages[], opinions{}, status, current_round, total_rounds, ...}.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

from backend.app.core import DEFAULT_PERSONAS, MAX_ROUNDS
from backend.app.core.errors import (
    DiscussionNotFoundError,
    InvalidRequestError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def _default_storage_dir() -> Path:
    return _repo_root() / "data" / "discussions"


def _agent_id_for_persona(persona: Any) -> str:
    name = getattr(persona, "name", str(persona))
    return str(name).lower().replace(" ", "_")


class DiscussionService:
    """Thin orchestration over the Week 2/3 core. No LLM/RAG/prompt logic here."""

    def __init__(
        self,
        persistence: Any | None = None,
        storage_dir: str | Path | None = None,
        agent_factory: Callable[[Any], Any] | None = None,
    ) -> None:
        # FilePersistence keeps discussions visible across HTTP requests and
        # matches Week 4 sentiment's expectation (loads run_id from disk).
        # InMemoryPersistence would vanish between TestClient calls otherwise.
        if persistence is not None:
            self.persistence = persistence
        else:
            from src.persistence import FilePersistence

            self.persistence = FilePersistence(
                storage_dir=str(storage_dir or _default_storage_dir())
            )
        # agent_factory(persona) -> agent with .respond()/.generate_opinion().
        # Tests inject stub agents; production builds real Week 2 Agents.
        self._agent_factory = agent_factory or self._default_agent_factory
        self._domain_index: dict[str, str | None] = {}
        self._load_domain_index()

    # ------------------------------------------------------------------ public

    def create_discussion(
        self,
        topic: str,
        num_rounds: int = 3,
        domain: str | None = None,
        personas: list[str] | None = None,
        enable_retrieval: bool = True,
    ) -> Any:
        """Run a REAL discussion through the Core Agent. No fake results."""
        clean_topic = (topic or "").strip()
        if not clean_topic:
            raise InvalidRequestError("Topic must be a non-empty string.")
        if not isinstance(num_rounds, int) or not 1 <= num_rounds <= MAX_ROUNDS:
            raise InvalidRequestError(
                f"num_rounds must be an integer between 1 and {MAX_ROUNDS}."
            )

        persona_names = list(personas) if personas else list(DEFAULT_PERSONAS)
        if not persona_names:
            raise InvalidRequestError("At least one persona is required.")
        if len(set(persona_names)) != len(persona_names):
            raise InvalidRequestError("Duplicate persona names are not allowed.")

        loaded_personas = self._load_personas(persona_names)
        agents = [self._agent_factory(p) for p in loaded_personas]
        agent_ids = [_agent_id_for_persona(a) for a in agents]

        from src.graph.topology import AgentGraph
        from src.routing.graph_router import GraphRouter
        from src.orchestration import DiscussionConfig, DiscussionOrchestrator

        try:
            graph = AgentGraph.create_persona_based_topology(agent_ids)
        except Exception as exc:
            raise ServiceUnavailableError(f"Failed to build discussion graph: {exc}") from exc
        if not graph.is_strongly_connected():
            raise ServiceUnavailableError("Discussion graph is not strongly connected.")

        config = DiscussionConfig(
            num_rounds=num_rounds,
            enable_retrieval=bool(enable_retrieval),
            enable_opinion_tracking=True,
        )
        orchestrator = DiscussionOrchestrator(
            router=GraphRouter(graph),
            persistence=self.persistence,
        )
        try:
            result = orchestrator.start_discussion(
                topic=clean_topic, agents=agents, config=config
            )
        except Exception as exc:
            logger.exception("Core discussion failed")
            raise ServiceUnavailableError(f"Core discussion failed: {exc}") from exc

        state = self._result_to_state(result)
        status = getattr(state, "status", None)
        status_value = getattr(status, "value", status)
        if isinstance(status_value, str) and status_value == "failed":
            raise ServiceUnavailableError(
                f"Core discussion failed: {getattr(state, 'error', 'unknown error')}"
            )

        # Normalize to the persisted DiscussionState so POST and GET return the
        # identical shape (total_rounds, timestamps, opinions) from one source.
        try:
            reloaded = self.persistence.load(state.discussion_id)
        except Exception:
            reloaded = None
        if reloaded is not None:
            state = reloaded

        if domain is not None:
            self._domain_index[state.discussion_id] = domain
            self._save_domain_index()
        return state

    def get_discussion(self, discussion_id: str) -> Any:
        discussion_id = (discussion_id or "").strip()
        if not discussion_id:
            raise InvalidRequestError("discussion_id must be a non-empty string.")
        try:
            state = self.persistence.load(discussion_id)
        except Exception as exc:
            logger.exception("Persistence load failed")
            raise ServiceUnavailableError(
                f"Discussion store unavailable: {exc}"
            ) from exc
        if state is None:
            raise DiscussionNotFoundError(discussion_id)
        return state

    def domain_for(self, discussion_id: str) -> str | None:
        return self._domain_index.get(discussion_id)

    # ------------------------------------------------------------------ internals

    def _load_personas(self, names: list[str]) -> list[Any]:
        try:
            from src.personas import list_personas, load_persona
        except Exception as exc:
            raise ServiceUnavailableError(
                f"Persona subsystem unavailable: {exc}"
            ) from exc
        try:
            available = set(list_personas())
        except Exception:
            available = set()
        unknown = [n for n in names if available and n not in available]
        if unknown:
            raise InvalidRequestError(
                f"Unknown persona(s): {', '.join(unknown)}. "
                f"Available: {', '.join(sorted(available))}"
            )
        loaded = []
        for name in names:
            try:
                loaded.append(load_persona(name))
            except FileNotFoundError as exc:
                raise InvalidRequestError(str(exc)) from exc
            except Exception as exc:
                raise ServiceUnavailableError(
                    f"Failed to load persona '{name}': {exc}"
                ) from exc
        return loaded

    def _default_agent_factory(self, persona: Any) -> Any:
        try:
            from src.agent import Agent
            from src.llm import get_provider
            from src.tools import RetrievalTool
        except Exception as exc:
            raise ServiceUnavailableError(
                f"Core agent subsystem unavailable: {exc}"
            ) from exc
        try:
            llm = get_provider()
        except ValueError as exc:
            # Missing/unknown provider or API key — a 503, not a 500.
            raise ServiceUnavailableError(
                "LLM provider unavailable (missing API key or unknown provider). "
                f"Set LLM_PROVIDER/LLM_API_KEY. Detail: {exc}"
            ) from exc
        except Exception as exc:
            raise ServiceUnavailableError(f"LLM provider failed: {exc}") from exc
        try:
            return Agent(persona=persona, llm=llm, tools=[RetrievalTool()])
        except Exception as exc:
            raise ServiceUnavailableError(f"Failed to build agent: {exc}") from exc

    @staticmethod
    def _result_to_state(result: Any) -> Any:
        # DiscussionResult has no .to_dict-preserving loader need; but callers
        # want a DiscussionState-like object. Re-load from persistence so the
        # returned object is exactly what GET would return (single source).
        return result

    # Small sidecar so `domain` (an API-level grouping, not a Week 3 field)
    # survives restarts without touching Week 3 models. In-memory-only when
    # the persistence backend has no storage dir (e.g. InMemoryPersistence
    # in tests) so tests never touch data/discussions/.
    def _domain_index_path(self) -> Path | None:
        storage = getattr(self.persistence, "storage_dir", None)
        if storage is None:
            return None
        return Path(storage) / "_backend_domains.json"

    def _load_domain_index(self) -> None:
        try:
            path = self._domain_index_path()
            if path is not None and path.exists():
                self._domain_index = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            self._domain_index = {}

    def _save_domain_index(self) -> None:
        try:
            path = self._domain_index_path()
            if path is None:
                return
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self._domain_index), encoding="utf-8")
        except Exception:
            logger.warning("Could not persist domain index", exc_info=True)
