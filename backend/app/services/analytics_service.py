"""Analytics adapter — consumes Week 4 through its public interface only.

The backend never reimplements agreement/influence/sentiment/opinion math.
It calls ``src.analytics.run_analytics`` (Hanaa's unified engine) and only
*adapts* the report into the API contract, plus builds the interaction graph
(a backend-owned derivation from messages + influence — not a Week 4 metric).

Week 4 reality handled honestly:
  - opinion/agreement/influence run deterministically (no LLM needed).
  - sentiment's registry entry has no matching function in
    src/metrics/sentiment.py (only run_id-based helpers), so the engine
    reports it as UNAVAILABLE — the API surfaces [] + status instead of
    inventing sentiment scores.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.app.core.errors import AnalyticsUnavailableError

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, discussion_service: Any) -> None:
        self.discussions = discussion_service

    # ------------------------------------------------------------------ public
    def get_analytics(self, discussion_id: str) -> dict:
        state = self.discussions.get_discussion(discussion_id)
        try:
            from src.analytics import run_analytics
        except Exception as exc:
            raise AnalyticsUnavailableError(
                f"Analytics subsystem unavailable: {exc}"
            ) from exc
        try:
            report = run_analytics(state)
        except Exception as exc:
            logger.exception("Analytics engine failed")
            raise AnalyticsUnavailableError(
                f"Analytics computation failed: {exc}"
            ) from exc

        try:
            payload = report.to_dict()
        except Exception as exc:
            raise AnalyticsUnavailableError(
                f"Analytics serialization failed: {exc}"
            ) from exc

        metrics = payload.get("metrics", {})
        summary = payload.get("summary", {})
        warnings = list(payload.get("warnings", []))

        opinion = self._adapt_opinion(metrics.get("opinion"))
        agreement = self._adapt_agreement(metrics.get("agreement"))
        influence = self._adapt_influence(metrics.get("influence"))
        sentiment = self._adapt_sentiment(metrics.get("sentiment"))
        interaction_graph = self._build_interaction_graph(state, influence)
        statuses = {
            name: {
                "status": (m or {}).get("status", "unavailable"),
                "error": (m or {}).get("error"),
            }
            for name, m in metrics.items()
        }

        state_dict = self._state_to_dict(state)
        return {
            "discussion_id": state_dict.get("discussion_id", discussion_id),
            "topic": state_dict.get("topic"),
            "generated_at": payload.get(
                "generated_at", datetime.now(timezone.utc).isoformat()
            ),
            "schema_version": payload.get("schema_version", "1.0"),
            "summary": summary,
            "opinion_trajectory": opinion,
            "agreement": agreement,
            "influence": influence,
            "sentiment": sentiment,
            "interaction_graph": interaction_graph,
            "metric_statuses": statuses,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------ adapters

    @staticmethod
    def _metric_data(metric: dict | None) -> Any:
        if not isinstance(metric, dict):
            return None
        if metric.get("status") != "ok":
            return None
        return metric.get("data")

    def _adapt_opinion(self, metric: dict | None) -> dict:
        """OpinionChangeResult.to_dict() -> {agent: [points]} (trajectories only)."""
        data = self._metric_data(metric)
        if data is None:
            return {}
        # Engine serializes OpinionChangeResult via to_jsonable(); depending on
        # version it may be {agent: [...]} or {trajectories: {...}, ...}.
        if isinstance(data, dict) and "trajectories" in data and isinstance(
            data["trajectories"], dict
        ):
            data = data["trajectories"]
        if not isinstance(data, dict):
            return {}
        out: dict[str, list[dict]] = {}
        for agent_id, points in data.items():
            if not isinstance(points, list):
                continue
            cleaned = []
            for p in points:
                if not isinstance(p, dict):
                    continue
                cleaned.append(
                    {
                        "agent_id": str(p.get("agent_id", agent_id)),
                        "agent_name": str(p.get("agent_name", agent_id)),
                        "round": p.get("round", 0),
                        "stance": p.get("stance"),
                        "change": p.get("change"),
                        "status": str(p.get("status", "ok")),
                        "n_cues": int(p.get("n_cues", 0) or 0),
                        "n_snapshots": int(p.get("n_snapshots", 1) or 1),
                    }
                )
            out[str(agent_id)] = cleaned
        return out

    def _adapt_agreement(self, metric: dict | None) -> list[dict]:
        data = self._metric_data(metric)
        if not isinstance(data, list):
            return []
        out = []
        for row in data:
            if not isinstance(row, dict):
                continue
            out.append(
                {
                    "round": row.get("round", 0),
                    "agreement_score": row.get("agreement_score"),
                    "mean_pairwise_difference": row.get("mean_pairwise_difference"),
                    "n_agents": int(row.get("n_agents", 0) or 0),
                    "n_valid": int(row.get("n_valid", 0) or 0),
                    "n_invalid": int(row.get("n_invalid", 0) or 0),
                    "status": str(row.get("status", "ok")),
                }
            )
        return sorted(out, key=lambda r: r["round"])

    def _adapt_influence(self, metric: dict | None) -> dict:
        data = self._metric_data(metric)
        if not isinstance(data, dict):
            return {}
        out = {}
        for agent_id, row in data.items():
            if not isinstance(row, dict):
                continue
            out[str(agent_id)] = {
                "agent_id": str(row.get("agent_id", agent_id)),
                "influence_score": row.get("influence_score"),
                "raw_pull": row.get("raw_pull"),
                "messages_sent": int(row.get("messages_sent", 0) or 0),
                "status": str(row.get("status", "ok")),
            }
        return out

    def _adapt_sentiment(self, metric: dict | None) -> list[dict]:
        # Sentiment is UNAVAILABLE in the current Week 4 registry (no matching
        # entry point) — return [] honestly; never synthesize scores.
        data = self._metric_data(metric)
        if not isinstance(data, list):
            return []
        out = []
        for row in data:
            if not isinstance(row, dict):
                continue
            out.append(
                {
                    "message_id": row.get("message_id"),
                    "agent_id": str(row.get("agent_id", "")),
                    "agent_name": str(row.get("agent_name", "")),
                    "round": row.get("round", 0),
                    "sentiment": str(row.get("sentiment", "neutral")),
                    "polarity": float(row.get("polarity", 0.0) or 0.0),
                    "summary": str(row.get("summary", "")),
                }
            )
        return out

    # Interaction graph is NOT a Week 4 metric — it is a backend derivation
    # from routed messages (recipient_id metadata from GraphRouter) so the
    # frontend dashboard gets nodes/edges without learning routing internals.
    def _build_interaction_graph(self, state: Any, influence: dict) -> dict:
        state_dict = self._state_to_dict(state)
        messages = state_dict.get("messages", [])
        participants = list(state_dict.get("participants", []))

        counts: dict[str, int] = {}
        names: dict[str, str] = {}
        edge_weights: dict[tuple[str, str], float] = {}
        for m in messages:
            if not isinstance(m, dict):
                continue
            sender = str(m.get("agent_id", ""))
            if not sender:
                continue
            counts[sender] = counts.get(sender, 0) + 1
            names[sender] = str(m.get("agent_name", sender))
            meta = m.get("metadata") or {}
            recipient = meta.get("recipient_id")
            if recipient:
                key = (sender, str(recipient))
                edge_weights[key] = edge_weights.get(key, 0.0) + 1.0

        for pid in participants:
            counts.setdefault(pid, 0)
            names.setdefault(pid, pid)

        # Fallback: no routing metadata (e.g. PassthroughRouter) — derive
        # undirected co-participation edges weighted by message volume so the
        # graph is still truthful about activity, marked kind="message".
        if not edge_weights and len(counts) >= 2:
            agents = sorted(counts)
            for i, a in enumerate(agents):
                for b in agents[i + 1 :]:
                    w = float(min(counts[a], counts[b]))
                    if w > 0:
                        edge_weights[(a, b)] = w

        nodes = [
            {
                "agent_id": aid,
                "agent_name": names.get(aid, aid),
                "message_count": counts.get(aid, 0),
                "influence_score": (influence.get(aid) or {}).get("influence_score"),
            }
            for aid in sorted(counts)
        ]
        edges = [
            {"source": s, "target": t, "weight": float(w), "kind": "message"}
            for (s, t), w in sorted(edge_weights.items())
        ]
        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def _state_to_dict(state: Any) -> dict:
        if isinstance(state, dict):
            return state
        to_dict = getattr(state, "to_dict", None)
        if callable(to_dict):
            try:
                result = to_dict()
                if isinstance(result, dict):
                    return result
            except Exception:
                pass
        return {}
