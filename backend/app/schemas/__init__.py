"""Pydantic API schemas — the stable frontend contract.

Conversion direction: internal Week 3 dataclasses -> these models -> JSON.
Internal objects are never returned directly.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ------------------------------------------------------------------ health/topics


class HealthResponse(BaseModel):
    status: str = Field(default="ok", examples=["ok"])


class TopicResponse(BaseModel):
    id: str = Field(examples=["industrial-decarbonization"])
    title: str = Field(examples=["Financing Industrial Decarbonization and Green Hydrogen"])
    domain: str = Field(examples=["mitigation"])
    description: str = ""
    suggested_personas: List[str] = Field(default_factory=list)


# ------------------------------------------------------------------ discussions


class CreateDiscussionRequest(BaseModel):
    """Matches the Core Agent contract: topic + DiscussionConfig(num_rounds)."""

    topic: str = Field(
        min_length=1,
        max_length=2000,
        examples=["Financing Industrial Decarbonization and Green Hydrogen"],
    )
    domain: Optional[str] = Field(default=None, examples=["mitigation"])
    num_rounds: int = Field(default=3, ge=1, le=10, examples=[3])
    personas: Optional[List[str]] = Field(
        default=None,
        examples=[["investor", "policy_expert", "scientist"]],
        description="Persona names from personas/*.json. Defaults to investor/policy_expert/scientist.",
    )
    enable_retrieval: bool = Field(default=True)

    model_config = {"extra": "forbid"}


class MessageResponse(BaseModel):
    message_id: str
    discussion_id: str
    round: int
    agent_id: str
    agent_name: str
    content: str
    timestamp: str
    in_response_to: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OpinionResponse(BaseModel):
    agent_id: str
    agent_name: str
    round: int
    opinion: str
    evidence: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    timestamp: str


class RoundResponse(BaseModel):
    round: int
    messages: List[MessageResponse] = Field(default_factory=list)


class DiscussionResponse(BaseModel):
    discussion_id: str
    topic: str
    domain: Optional[str] = None
    participants: List[str] = Field(default_factory=list)
    rounds_completed: int
    total_rounds: int
    status: str
    rounds: List[RoundResponse] = Field(default_factory=list)
    messages: List[MessageResponse] = Field(default_factory=list)
    opinions: Dict[str, List[OpinionResponse]] = Field(default_factory=dict)
    started_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


# ------------------------------------------------------------------ analytics


class StancePointResponse(BaseModel):
    agent_id: str
    agent_name: str = ""
    round: int
    stance: Optional[float] = None
    change: Optional[float] = None
    status: str = "ok"
    n_cues: int = 0
    n_snapshots: int = 1


class AgreementRoundResponse(BaseModel):
    round: int
    agreement_score: Optional[float] = None
    mean_pairwise_difference: Optional[float] = None
    n_agents: int = 0
    n_valid: int = 0
    n_invalid: int = 0
    status: str = "ok"


class InfluenceResponse(BaseModel):
    agent_id: str
    influence_score: Optional[float] = None
    raw_pull: Optional[float] = None
    messages_sent: int = 0
    status: str = "ok"


class SentimentRowResponse(BaseModel):
    message_id: Optional[str] = None
    agent_id: str
    agent_name: str = ""
    round: int
    sentiment: str = "neutral"
    polarity: float = 0.0
    summary: str = ""


class InteractionNodeResponse(BaseModel):
    agent_id: str
    agent_name: str = ""
    message_count: int = 0
    influence_score: Optional[float] = None


class InteractionEdgeResponse(BaseModel):
    source: str
    target: str
    weight: float = 0.0
    kind: str = Field(default="message", examples=["message", "influence"])


class InteractionGraphResponse(BaseModel):
    nodes: List[InteractionNodeResponse] = Field(default_factory=list)
    edges: List[InteractionEdgeResponse] = Field(default_factory=list)


class MetricStatusResponse(BaseModel):
    status: str
    error: Optional[str] = None


class AnalyticsResponse(BaseModel):
    discussion_id: str
    topic: Optional[str] = None
    generated_at: str
    schema_version: str = "1.0"
    summary: Dict[str, Any] = Field(default_factory=dict)
    opinion_trajectory: Dict[str, List[StancePointResponse]] = Field(default_factory=dict)
    agreement: List[AgreementRoundResponse] = Field(default_factory=list)
    influence: Dict[str, InfluenceResponse] = Field(default_factory=dict)
    sentiment: List[SentimentRowResponse] = Field(default_factory=list)
    interaction_graph: InteractionGraphResponse = Field(default_factory=InteractionGraphResponse)
    metric_statuses: Dict[str, MetricStatusResponse] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


# ------------------------------------------------------------------ errors


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
