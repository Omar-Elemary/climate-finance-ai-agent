"""
src/analytics/engine.py
OWNER: HANAA

The unified analytics engine.

One entry point, one output object:

    from src.analytics import run_analytics
    report = run_analytics(history)          # history = DiscussionState or dict
    report.to_dict()                         # -> JSON for Ziad's markdown report

Design rules:
  * The engine NEVER contains metric math. It validates, dispatches, wraps.
  * Every metric is optional. If a teammate's module does not exist yet, or
    raises, that metric comes back status="unavailable"/"error" and the rest
    of the report is still produced. One broken file must not kill the run.
  * Metric modules are imported lazily, inside run(), for the same reason.
  * Metric functions receive the ORIGINAL history object (DiscussionState or
    dict), because that is the contract src/metrics/ already documents.
"""

from __future__ import annotations

import importlib
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from .contracts import (
    ALL_METRICS,
    METRIC_AGREEMENT,
    METRIC_INFLUENCE,
    METRIC_OPINION,
    METRIC_SENTIMENT,
    AnalyticsReport,
    MetricResult,
    MetricStatus,
)
from .validation import ValidationError, validate_history


@dataclass(frozen=True)
class MetricSpec:
    """How to find and call one teammate's metric."""

    name: str
    module: str
    functions: Sequence[str]   # candidate entry points, tried in order


# Registry. Adding a fifth metric later = one line here, nothing else.
METRIC_REGISTRY: Dict[str, MetricSpec] = {
    METRIC_OPINION: MetricSpec(
        name=METRIC_OPINION,
        module="src.metrics.opinion",
        functions=("calculate_opinion_change", "calculate_opinion", "opinion_change"),
    ),
    METRIC_AGREEMENT: MetricSpec(
        name=METRIC_AGREEMENT,
        module="src.metrics.agreement",
        functions=("calculate_agreement", "agreement", "compute_agreement"),
    ),
    METRIC_INFLUENCE: MetricSpec(
        name=METRIC_INFLUENCE,
        module="src.metrics.influence",
        functions=("calculate_influence", "calculate_agent_influence",
                   "compute_influence", "influence"),
    ),
    METRIC_SENTIMENT: MetricSpec(
        name=METRIC_SENTIMENT,
        module="src.metrics.sentiment",
        functions=("calculate_sentiment", "analyze_sentiment",
                   "compute_sentiment", "sentiment"),
    ),
}


class AnalyticsEngine:
    """Validates a discussion history, runs every available metric, returns one report."""

    def __init__(
        self,
        metrics: Optional[Iterable[str]] = None,
        registry: Optional[Dict[str, MetricSpec]] = None,
        metric_callables: Optional[Dict[str, Callable[[Any], Any]]] = None,
        strict: bool = False,
    ) -> None:
        """
        metrics          which metrics to run (default: all four)
        registry         override module/function lookup
        metric_callables inject callables directly — used by tests and by anyone
                         who wants to plug in a metric without a module path
        strict           raise on an invalid input instead of returning a report
                         that carries the errors
        """
        self.metric_names: List[str] = list(metrics) if metrics else list(ALL_METRICS)
        self.registry = dict(registry or METRIC_REGISTRY)
        self.metric_callables = dict(metric_callables or {})
        self.strict = strict

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run(self, history: Any) -> AnalyticsReport:
        """Validate, then run each metric in isolation. Never raises unless strict."""
        validation = validate_history(history, strict=self.strict)

        report = AnalyticsReport(
            summary=validation.summary,
            errors=list(validation.errors),
            warnings=list(validation.warnings),
        )

        if not validation.is_valid:
            reason = "invalid input: " + "; ".join(validation.errors)
            for name in self.metric_names:
                report.metrics[name] = MetricResult.unavailable(name, reason)
            return report

        for name in self.metric_names:
            report.metrics[name] = self._run_one(name, history)

        return report

    def available_metrics(self) -> Dict[str, bool]:
        """Which teammates' modules are importable right now. Handy for debugging."""
        status: Dict[str, bool] = {}
        for name in self.metric_names:
            if name in self.metric_callables:
                status[name] = True
                continue
            func, _ = self._resolve(name)
            status[name] = func is not None
        return status

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _resolve(self, name: str):
        """Find the callable for a metric. Returns (callable|None, source_or_reason)."""
        if name in self.metric_callables:
            return self.metric_callables[name], f"injected:{name}"

        spec = self.registry.get(name)
        if spec is None:
            return None, f"no registry entry for metric '{name}'"

        try:
            module = importlib.import_module(spec.module)
        except ImportError as exc:
            return None, f"{spec.module} not importable yet ({exc})"
        except Exception as exc:  # module exists but blew up at import time
            return None, f"{spec.module} failed to import ({type(exc).__name__}: {exc})"

        for func_name in spec.functions:
            func = getattr(module, func_name, None)
            if callable(func):
                return func, f"{spec.module}.{func_name}"

        return None, (
            f"{spec.module} has none of: {', '.join(spec.functions)}"
        )

    def _run_one(self, name: str, history: Any) -> MetricResult:
        func, source = self._resolve(name)
        if func is None:
            return MetricResult.unavailable(name, source)

        started = time.perf_counter()
        try:
            data = func(history)
        except Exception as exc:
            if self.strict:
                raise
            return MetricResult.failed(
                name, f"{type(exc).__name__}: {exc}", source=source
            )
        duration_ms = round((time.perf_counter() - started) * 1000, 3)

        result = MetricResult.success(name, data, source=source,
                                      duration_ms=duration_ms)
        # Respect a metric that reports its own insufficiency.
        if result.ok and _declares_insufficient(data):
            result.status = MetricStatus.INSUFFICIENT_DATA
        return result


def _declares_insufficient(data: Any) -> bool:
    """Detect a metric that returned status='insufficient_data' for everything."""
    statuses: List[str] = []

    def _status_of(item: Any) -> Optional[str]:
        if isinstance(item, dict):
            return item.get("status")
        return getattr(item, "status", None)

    if isinstance(data, dict):
        top = _status_of(data)
        if isinstance(top, str):
            return top == "insufficient_data"
        for value in data.values():
            status = _status_of(value)
            if isinstance(status, str):
                statuses.append(status)
    elif isinstance(data, list):
        for item in data:
            status = _status_of(item)
            if isinstance(status, str):
                statuses.append(status)
    else:
        status = _status_of(data)
        if isinstance(status, str):
            return status == "insufficient_data"

    return bool(statuses) and all(s == "insufficient_data" for s in statuses)


# --------------------------------------------------------------------------- #
# Convenience function — what Ziad and the demos should call
# --------------------------------------------------------------------------- #

def run_analytics(
    history: Any,
    metrics: Optional[Iterable[str]] = None,
    strict: bool = False,
    **kwargs: Any,
) -> AnalyticsReport:
    """Run the full analytics pipeline on one discussion history."""
    return AnalyticsEngine(metrics=metrics, strict=strict, **kwargs).run(history)


def run_analytics_from_file(path: str, **kwargs: Any) -> AnalyticsReport:
    """Load a Week 3 data/discussions/<id>.json and analyze it."""
    import json

    with open(path, "r", encoding="utf-8") as handle:
        history = json.load(handle)
    return run_analytics(history, **kwargs)


__all__ = [
    "AnalyticsEngine",
    "MetricSpec",
    "METRIC_REGISTRY",
    "run_analytics",
    "run_analytics_from_file",
    "ValidationError",
]
