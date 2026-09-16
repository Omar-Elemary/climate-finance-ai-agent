"""
src/analytics/contracts.py
OWNER: HANAA

Shared data contracts for the analytics layer.

This module is the single source of truth for:
  1. what an "analytics input" (a Week 3 discussion history) must look like, and
  2. what the unified engine returns to reporting / visualization.

It contains NO metric logic and imports NO metric module, so it can be
imported by everyone (Ola, Omar E., Omar M., Ziad) without circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

# Bump when the shape of AnalyticsReport.to_dict() changes.
SCHEMA_VERSION = "1.0"

# Canonical metric names. Reporting/visualization should key off these.
METRIC_OPINION = "opinion"
METRIC_AGREEMENT = "agreement"
METRIC_INFLUENCE = "influence"
METRIC_SENTIMENT = "sentiment"

ALL_METRICS = (METRIC_OPINION, METRIC_AGREEMENT, METRIC_INFLUENCE, METRIC_SENTIMENT)


class MetricStatus(str, Enum):
    """Per-metric outcome. Mirrors the vocabulary used inside src/metrics/."""

    OK = "ok"                              # ran, produced data
    INSUFFICIENT_DATA = "insufficient_data"  # ran, but not enough rounds/agents
    UNAVAILABLE = "unavailable"            # teammate's module not importable yet
    ERROR = "error"                        # raised an exception


# --------------------------------------------------------------------------- #
# Normalized input contract
# --------------------------------------------------------------------------- #

@dataclass
class OpinionSnapshot:
    """One agent's opinion at one round, after key normalization."""

    agent_id: str
    round: int
    stance: Optional[float] = None
    opinion: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageRecord:
    """One routed message, after key normalization."""

    agent_id: str
    round: int
    content: Optional[str] = None
    recipient_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscussionSummary:
    """Cheap descriptive facts about the discussion, computed by validation.py."""

    discussion_id: Optional[str] = None
    topic: Optional[str] = None
    agent_ids: List[str] = field(default_factory=list)
    rounds: List[int] = field(default_factory=list)
    n_agents: int = 0
    n_rounds: int = 0
    n_opinions: int = 0
    n_messages: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedHistory:
    """
    The engine's internal view of the input.

    NOTE: metric modules are still handed the ORIGINAL history object, because
    Omar's metrics accept a DiscussionState or its to_dict(). This normalized
    view exists for validation, summaries and reporting metadata only.
    """

    raw: Any
    as_dict: Dict[str, Any] = field(default_factory=dict)
    opinions: List[OpinionSnapshot] = field(default_factory=list)
    messages: List[MessageRecord] = field(default_factory=list)
    summary: DiscussionSummary = field(default_factory=DiscussionSummary)


# --------------------------------------------------------------------------- #
# Output contract
# --------------------------------------------------------------------------- #

@dataclass
class MetricResult:
    """Uniform wrapper around whatever a metric module returns."""

    name: str
    status: MetricStatus = MetricStatus.OK
    data: Any = None
    error: Optional[str] = None
    source: Optional[str] = None          # e.g. "src.metrics.opinion.calculate_opinion_change"
    duration_ms: Optional[float] = None

    @property
    def ok(self) -> bool:
        return self.status == MetricStatus.OK

    @classmethod
    def success(cls, name: str, data: Any, source: str = None,
                duration_ms: float = None) -> "MetricResult":
        status = MetricStatus.OK
        if data is None or (isinstance(data, (dict, list)) and len(data) == 0):
            status = MetricStatus.INSUFFICIENT_DATA
        return cls(name=name, status=status, data=data,
                   source=source, duration_ms=duration_ms)

    @classmethod
    def unavailable(cls, name: str, reason: str) -> "MetricResult":
        return cls(name=name, status=MetricStatus.UNAVAILABLE, data=None, error=reason)

    @classmethod
    def failed(cls, name: str, reason: str, source: str = None) -> "MetricResult":
        return cls(name=name, status=MetricStatus.ERROR, data=None,
                   error=reason, source=source)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "data": to_jsonable(self.data),
            "error": self.error,
            "source": self.source,
            "duration_ms": self.duration_ms,
        }


@dataclass
class AnalyticsReport:
    """What AnalyticsEngine.run() returns — the contract Ziad consumes."""

    summary: DiscussionSummary = field(default_factory=DiscussionSummary)
    metrics: Dict[str, MetricResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)      # input contract violations
    warnings: List[str] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    schema_version: str = SCHEMA_VERSION

    # -- convenience accessors (so reporting never touches .metrics["x"].data raw)
    def get(self, name: str) -> Optional[MetricResult]:
        return self.metrics.get(name)

    def data(self, name: str, default: Any = None) -> Any:
        result = self.metrics.get(name)
        return result.data if result is not None and result.ok else default

    @property
    def opinion(self) -> Any:
        return self.data(METRIC_OPINION)

    @property
    def agreement(self) -> Any:
        return self.data(METRIC_AGREEMENT)

    @property
    def influence(self) -> Any:
        return self.data(METRIC_INFLUENCE)

    @property
    def sentiment(self) -> Any:
        return self.data(METRIC_SENTIMENT)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def statuses(self) -> Dict[str, str]:
        return {name: r.status.value for name, r in self.metrics.items()}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "summary": self.summary.to_dict(),
            "metrics": {name: r.to_dict() for name, r in self.metrics.items()},
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


# --------------------------------------------------------------------------- #
# Serialization helper
# --------------------------------------------------------------------------- #

def to_jsonable(value: Any) -> Any:
    """
    Recursively convert metric output into JSON-safe primitives.

    Needed because teammates return their own dataclasses (e.g. Ola's
    AgentInfluence) or enums, and reporting/markdown.py must be able to
    json.dump() the whole report.
    """
    # Enum first: MetricStatus subclasses str, so the primitive check below
    # would otherwise swallow it and leak "MetricStatus.OK" instead of "ok".
    if isinstance(value, Enum):
        return to_jsonable(value.value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            return to_jsonable(value.to_dict())
        except Exception:  # pragma: no cover - defensive
            pass
    if hasattr(value, "__dict__"):
        return {k: to_jsonable(v) for k, v in vars(value).items()
                if not k.startswith("_")}
    return str(value)
