"""agent_core — Persona 1 (Core Agent / Integration), Week 5.

Stable public boundary around the existing Week 1 (RAG) + Week 2 (Agent) +
Week 3 (discussion engine) systems. The backend consumes this; it never
reaches into ``src.*`` internals directly.

Public surface::

    from agent_core import (
        CoreDiscussionService,   # create_discussion / get_discussion
        DiscussionRequest,       # request contract (topic + DiscussionConfig)
        DiscussionState,         # result contract (Week 3 state, .to_dict())
        ...
    )

Ownership: Persona 1 owns ONLY ``agent_core/``. Never imports ``backend/``.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agent_core.exceptions import (
    AgentExecutionError,
    CoreError,
    DiscussionExecutionError,
    DiscussionNotFound,
    InvalidDiscussionRequest,
    RetrievalError,
)
from agent_core.schemas import (
    DEFAULT_PERSONAS,
    MAX_ROUNDS,
    DiscussionConfig,
    DiscussionRequest,
    DiscussionResult,
    DiscussionState,
    DiscussionStatus,
    Message,
    OpinionRecord,
    RetrievalEvent,
    agents_view,
    messages_view,
    retrieval_context_view,
    rounds_view,
)
from agent_core.service import CoreDiscussionService, agent_id_for_persona

__all__ = [
    "CoreDiscussionService",
    "DiscussionRequest",
    "DiscussionState",
    "DiscussionResult",
    "DiscussionConfig",
    "DiscussionStatus",
    "Message",
    "OpinionRecord",
    "RetrievalEvent",
    "agents_view",
    "rounds_view",
    "messages_view",
    "retrieval_context_view",
    "agent_id_for_persona",
    "DEFAULT_PERSONAS",
    "MAX_ROUNDS",
    "CoreError",
    "InvalidDiscussionRequest",
    "DiscussionNotFound",
    "DiscussionExecutionError",
    "AgentExecutionError",
    "RetrievalError",
]
