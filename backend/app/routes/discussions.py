"""Discussion routes — thin: validate via schemas, delegate to service, adapt."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Path

from backend.app.core.errors import BackendError
from backend.app.dependencies import get_discussion_service
from backend.app.schemas import (
    CreateDiscussionRequest,
    DiscussionResponse,
    MessageResponse,
    OpinionResponse,
    RoundResponse,
)
from backend.app.services.discussion_service import DiscussionService

router = APIRouter(tags=["discussions"])


def _adapt_state(state: Any, domain: str | None) -> DiscussionResponse:
    d = state.to_dict() if hasattr(state, "to_dict") else dict(state)
    messages = [
        MessageResponse(
            message_id=m.get("message_id", ""),
            discussion_id=m.get("discussion_id", d.get("discussion_id", "")),
            round=int(m.get("round", 0)),
            agent_id=str(m.get("agent_id", "")),
            agent_name=str(m.get("agent_name", "")),
            content=str(m.get("content", "")),
            timestamp=str(m.get("timestamp", "")),
            in_response_to=m.get("in_response_to"),
            metadata=dict(m.get("metadata", {}) or {}),
        )
        for m in d.get("messages", [])
        if isinstance(m, dict)
    ]
    by_round: dict[int, list[MessageResponse]] = {}
    for msg in messages:
        by_round.setdefault(msg.round, []).append(msg)
    rounds = [
        RoundResponse(round=r, messages=by_round[r]) for r in sorted(by_round)
    ]
    opinions: dict[str, list[OpinionResponse]] = {}
    raw_opinions = d.get("opinions", {}) or {}
    for agent_id, records in raw_opinions.items():
        adapted = []
        for o in records or []:
            if not isinstance(o, dict):
                continue
            adapted.append(
                OpinionResponse(
                    agent_id=str(o.get("agent_id", agent_id)),
                    agent_name=str(o.get("agent_name", agent_id)),
                    round=int(o.get("round", 0)),
                    opinion=str(o.get("opinion", "")),
                    evidence=list(o.get("evidence", []) or []),
                    sources=list(o.get("sources", []) or []),
                    timestamp=str(o.get("timestamp", "")),
                )
            )
        opinions[str(agent_id)] = adapted
    return DiscussionResponse(
        discussion_id=str(d.get("discussion_id", "")),
        topic=str(d.get("topic", "")),
        domain=domain,
        participants=list(d.get("participants", []) or []),
        rounds_completed=int(d.get("current_round", d.get("rounds_completed", 0)) or 0),
        # DiscussionResult.to_dict() carries rounds_completed (no total_rounds);
        # DiscussionState.to_dict() carries total_rounds. Accept both.
        total_rounds=int(d.get("total_rounds", d.get("rounds_completed", 0)) or 0),
        status=str(d.get("status", "")),
        rounds=rounds,
        messages=messages,
        opinions=opinions,
        started_at=str(d.get("started_at", "")),
        completed_at=d.get("completed_at"),
        error=d.get("error"),
    )


@router.post(
    "/discussions",
    response_model=DiscussionResponse,
    status_code=201,
    summary="Create a discussion",
    response_description="Discussion created through the Core Agent",
)
def create_discussion(
    body: CreateDiscussionRequest,
    service: DiscussionService = Depends(get_discussion_service),
) -> DiscussionResponse:
    state = service.create_discussion(
        topic=body.topic,
        num_rounds=body.num_rounds,
        domain=body.domain,
        personas=body.personas,
        enable_retrieval=body.enable_retrieval,
    )
    domain = body.domain
    if domain is None and hasattr(service, "domain_for"):
        try:
            domain = service.domain_for(state.discussion_id)
        except Exception:
            domain = None
    return _adapt_state(state, domain)


@router.get(
    "/discussions/{discussion_id}",
    response_model=DiscussionResponse,
    summary="Get a discussion",
    response_description="Discussion result from the Core Agent",
)
def get_discussion(
    discussion_id: str = Path(min_length=1, examples=["test-run-001"]),
    service: DiscussionService = Depends(get_discussion_service),
) -> DiscussionResponse:
    state = service.get_discussion(discussion_id)
    domain = None
    if hasattr(service, "domain_for"):
        try:
            domain = service.domain_for(
                state.discussion_id
                if hasattr(state, "discussion_id")
                else discussion_id
            )
        except BackendError:
            raise
        except Exception:
            domain = None
    return _adapt_state(state, domain)
