"""
src/analytics/__init__.py
OWNER: HANAA

Public surface of the analytics layer.

    from src.analytics import run_analytics, AnalyticsEngine, AnalyticsReport

Re-exports only — no logic lives here.
"""

from .contracts import (
    ALL_METRICS,
    METRIC_AGREEMENT,
    METRIC_INFLUENCE,
    METRIC_OPINION,
    METRIC_SENTIMENT,
    SCHEMA_VERSION,
    AnalyticsReport,
    DiscussionSummary,
    MessageRecord,
    MetricResult,
    MetricStatus,
    NormalizedHistory,
    OpinionSnapshot,
    to_jsonable,
)
from .engine import (
    METRIC_REGISTRY,
    AnalyticsEngine,
    MetricSpec,
    run_analytics,
    run_analytics_from_file,
)
from .validation import (
    ValidationError,
    ValidationResult,
    is_valid_history,
    validate_history,
)

__all__ = [
    # engine
    "AnalyticsEngine",
    "MetricSpec",
    "METRIC_REGISTRY",
    "run_analytics",
    "run_analytics_from_file",
    # contracts
    "AnalyticsReport",
    "MetricResult",
    "MetricStatus",
    "DiscussionSummary",
    "NormalizedHistory",
    "OpinionSnapshot",
    "MessageRecord",
    "to_jsonable",
    "SCHEMA_VERSION",
    "ALL_METRICS",
    "METRIC_OPINION",
    "METRIC_AGREEMENT",
    "METRIC_INFLUENCE",
    "METRIC_SENTIMENT",
    # validation
    "validate_history",
    "is_valid_history",
    "ValidationResult",
    "ValidationError",
]