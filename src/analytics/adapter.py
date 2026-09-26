"""
src/analytics/adapter.py
OWNER: HANAA — Week 5, analytics adapter + graph data

Turns Week 4 analytics output into the frontend JSON defined in
response_format.py.

    from src.analytics.adapter import build_analytics_response
    payload = build_analytics_response(analytics, history)
    # FastAPI:   return payload
    # Streamlit: st.line_chart(...) from payload["opinion_trajectory"]

`analytics` can be ANY of the shapes the team currently produces:
  * AnalyticsReport              <- src/analytics/engine.py (run_analytics)
  * AnalyticsReport.to_dict()
  * dict of objects              <- src/analytics/unified.py (analyze)
  * dict of plain dicts          <- src/analytics/unified.py (analyze_to_dict)

`history` is the Week 3 discussion (DiscussionState or its to_dict()).
It is optional, but the interaction graph's edges come from its messages.

Rules:
  * NO analytics are recalculated here (Week 5 README, section 26).
    The adapter only reads, renames, sorts and groups for display.
  * One section failing never breaks the others: a section whose data
    cannot be read comes back with status "error" and a message.
  * The result is plain JSON: dicts, lists, str, int, float, bool, None.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from enum import Enum
from itertools import combinations
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .response_format import (
    KNOWN_STATUSES,
    RESPONSE_SCHEMA_VERSION,
    SECTION_ERROR,
    SECTION_INSUFFICIENT,
    SECTION_NAMES,
    SECTION_OK,
    SECTION_UNAVAILABLE,
    empty_section,
)

logger = logging.getLogger(__name__)

# (status, data, error) for one metric, before formatting
RawMetric = Tuple[str, Any, Optional[str]]

# Week 4 metric name -> keys it may appear under in unified.py output
_UNIFIED_KEYS = {
    "opinion": ("opinion_change", "opinion"),
    "agreement": ("agreement",),
    "influence": ("influence",),
    "sentiment": ("sentiment",),
}

_SENTIMENT_LABELS = ("positive", "negative", "neutral")
_RECIPIENT_KEYS = ("recipient_id", "recipient", "to", "recipients", "recipient_ids")


# --------------------------------------------------------------------------- #
# Small readers — work on objects AND dicts
# --------------------------------------------------------------------------- #

def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _num(value: Any, digits: int = 4) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return round(float(value), digits)


def _int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return None


def _status_text(value: Any) -> str:
    if isinstance(value, Enum):
        value = value.value
    text = str(value) if value is not None else SECTION_UNAVAILABLE
    return text if text in KNOWN_STATUSES else SECTION_ERROR


def _mean(values: List[float]) -> Optional[float]:
    return round(sum(values) / len(values), 4) if values else None


# --------------------------------------------------------------------------- #
# 1. Read whichever engine output we were given
# --------------------------------------------------------------------------- #

def _read_analytics(analytics: Any) -> Tuple[Dict[str, RawMetric], Dict[str, Any]]:
    """Return ({metric: (status, data, error)}, meta) for any supported shape."""
    meta: Dict[str, Any] = {"discussion_id": None, "topic": None, "agents": [],
                            "rounds": [], "warnings": [], "errors": []}
    raw: Dict[str, RawMetric] = {}

    if analytics is None:
        for name in _UNIFIED_KEYS:
            raw[name] = (SECTION_UNAVAILABLE, None, "no analytics result was provided")
        return raw, meta

    metrics = _get(analytics, "metrics")

    # --- engine.py: AnalyticsReport or its to_dict() ---------------------- #
    if isinstance(metrics, dict):
        summary = _get(analytics, "summary")
        meta["discussion_id"] = _get(summary, "discussion_id")
        meta["topic"] = _get(summary, "topic")
        meta["agents"] = list(_get(summary, "agent_ids") or [])
        meta["rounds"] = list(_get(summary, "rounds") or [])
        meta["warnings"] = list(_get(analytics, "warnings") or [])
        meta["errors"] = list(_get(analytics, "errors") or [])
        for name in _UNIFIED_KEYS:
            result = metrics.get(name)
            if result is None:
                raw[name] = (SECTION_UNAVAILABLE, None, f"metric '{name}' was not run")
            else:
                raw[name] = (_status_text(_get(result, "status")),
                             _get(result, "data"), _get(result, "error"))
        return raw, meta

    # --- unified.py: {'opinion_change': ..., 'agreement': ..., ...} ------- #
    if isinstance(analytics, dict):
        for name, keys in _UNIFIED_KEYS.items():
            key = next((k for k in keys if k in analytics), None)
            if key is None:
                raw[name] = (SECTION_UNAVAILABLE, None,
                             f"'{keys[0]}' missing from analytics result")
                continue
            data = analytics[key]
            empty = data is None or (isinstance(data, (list, dict)) and not data)
            raw[name] = (SECTION_INSUFFICIENT if empty else SECTION_OK, data,
                         "metric returned no data" if empty else None)
        return raw, meta

    for name in _UNIFIED_KEYS:
        raw[name] = (SECTION_ERROR, None,
                     f"unsupported analytics type: {type(analytics).__name__}")
    return raw, meta


# --------------------------------------------------------------------------- #
# 2. Read the Week 3 history (only for names, topic, and graph edges)
# --------------------------------------------------------------------------- #

def _history_messages(history: Any) -> List[Any]:
    messages = _get(history, "messages")
    return list(messages) if isinstance(messages, (list, tuple)) else []


def _history_agent_names(history: Any) -> Dict[str, str]:
    names: Dict[str, str] = {}
    opinions = _get(history, "opinions")
    if isinstance(opinions, dict):
        for agent_id, records in opinions.items():
            for record in records or []:
                name = _get(record, "agent_name")
                if name:
                    names.setdefault(str(agent_id), str(name))
    for message in _history_messages(history):
        agent_id, name = _get(message, "agent_id"), _get(message, "agent_name")
        if agent_id and name:
            names.setdefault(str(agent_id), str(name))
    return names


def _recipients(message: Any) -> List[str]:
    """Recipient ids of one message, wherever Week 3 stored them."""
    found: List[str] = []
    for container in (message, _get(message, "metadata")):
        if container is None:
            continue
        for key in _RECIPIENT_KEYS:
            value = _get(container, key)
            if isinstance(value, str) and value:
                found.append(value)
            elif isinstance(value, (list, tuple)):
                found.extend(str(v) for v in value if v)
    return list(dict.fromkeys(found))  # de-duplicate, keep order


# --------------------------------------------------------------------------- #
# 3. One formatter per section
# --------------------------------------------------------------------------- #

def _format_opinion(data: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:
    trajectories = _get(data, "trajectories")
    summaries = _get(data, "summaries") or {}
    if trajectories is None:
        if not isinstance(data, dict):
            raise TypeError(f"unexpected opinion data: {type(data).__name__}")
        trajectories = data  # OpinionChangeResult.to_dict() -> {agent: [points]}

    series = []
    for agent_id in sorted(trajectories):
        agent_id_str = str(agent_id)
        points, name = [], None
        for point in trajectories[agent_id] or []:
            round_no = _int(_get(point, "round"))
            if round_no is None:
                continue
            name = name or _get(point, "agent_name")
            ok = _get(point, "status", SECTION_OK) == SECTION_OK
            points.append({
                "round": round_no,
                "stance": _num(_get(point, "stance")) if ok else None,
                "change": _num(_get(point, "change")) if ok else None,
            })
        points.sort(key=lambda p: p["round"])
        if name:
            ctx["agent_names"].setdefault(agent_id_str, str(name))

        valid = [p["stance"] for p in points if p["stance"] is not None]
        summary = summaries.get(agent_id) if isinstance(summaries, dict) else None
        if summary is not None:
            initial = _num(_get(summary, "initial_stance"))
            final = _num(_get(summary, "final_stance"))
            total = _num(_get(summary, "total_movement"))
            direction = _get(summary, "direction")
        else:  # unified.analyze_to_dict() drops summaries: read first/last point
            initial = valid[0] if valid else None
            final = valid[-1] if valid else None
            total = round(final - initial, 4) if valid else None
            direction = None

        series.append({
            "agent_id": agent_id_str,
            "agent_name": ctx["agent_names"].get(agent_id_str, agent_id_str),
            "points": points,
            "initial": initial,
            "final": final,
            "total_change": total,
            "direction": direction,
        })

    has_data = any(p["stance"] is not None for s in series for p in s["points"])
    return {
        "status": SECTION_OK if has_data else SECTION_INSUFFICIENT,
        "error": None if has_data else "no valid stances in any round",
        "series": series,
    }


def _format_agreement(data: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(data, dict) and all(isinstance(v, (int, float)) for v in data.values()):
        items = [{"round": k, "agreement_score": v, "status": SECTION_OK}
                 for k, v in data.items()]           # plain {round: score}
    elif isinstance(data, dict):
        items = list(data.values())
    elif isinstance(data, (list, tuple)):
        items = list(data)
    else:
        raise TypeError(f"unexpected agreement data: {type(data).__name__}")

    rows = []
    for item in items:
        round_no = _int(_get(item, "round"))
        if round_no is None:
            continue
        score = _get(item, "agreement_score")
        if score is None:
            score = _get(item, "score")
        rows.append({
            "round": round_no,
            "score": _num(score),
            "status": _status_text(_get(item, "status", SECTION_OK)),
            "n_valid": _int(_get(item, "n_valid")),
        })
    rows.sort(key=lambda r: r["round"])

    scores = [r["score"] for r in rows if r["score"] is not None]
    return {
        "status": SECTION_OK if scores else SECTION_INSUFFICIENT,
        "error": None if scores else "no round had at least two valid stances",
        "rounds": rows,
        "final": scores[-1] if scores else None,
        "mean": _mean(scores),
    }


def _format_influence(data: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(data, dict):
        items = list(data.items())
    elif isinstance(data, (list, tuple)):
        items = [(_get(x, "agent_id"), x) for x in data]
    else:
        raise TypeError(f"unexpected influence data: {type(data).__name__}")

    rows = []
    for key, item in items:
        agent_id = str(_get(item, "agent_id") or key)
        score = _num(_get(item, "influence_score"))
        messages_sent = _int(_get(item, "messages_sent"))
        rows.append({
            "agent_id": agent_id,
            "agent_name": ctx["agent_names"].get(agent_id, agent_id),
            "score": score,
            "raw_pull": _num(_get(item, "raw_pull")),
            "messages_sent": messages_sent,
            "status": _status_text(_get(item, "status", SECTION_OK)),
        })
        ctx["influence"][agent_id] = score
        if messages_sent is not None:
            ctx["messages_sent"][agent_id] = messages_sent

    # highest first; agents without a score last; ties alphabetical
    rows.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0.0), r["agent_id"]))
    scores = [r["score"] for r in rows if r["score"] is not None]
    return {
        "status": SECTION_OK if scores else SECTION_INSUFFICIENT,
        "error": None if scores else "influence needs at least 2 agents and 2 rounds",
        "agents": rows,
        "all_equal": len(scores) > 1 and len(set(scores)) == 1,
    }


def _group(rows: List[Dict[str, Any]], key: Callable[[Dict], str],
           label: Callable[[str], str]) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[key(row)].append(row)
    out = []
    for group_key, members in groups.items():
        polarities = [m["polarity"] for m in members if m["polarity"] is not None]
        labels = Counter(m["sentiment"] for m in members)
        out.append({
            "key": group_key,
            "label": label(group_key),
            "mean_polarity": _mean(polarities),
            "n_messages": len(members),
            "dominant": labels.most_common(1)[0][0] if labels else None,
        })
    return out


def _format_sentiment(data: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, (list, tuple)):
        raise TypeError(f"unexpected sentiment data: {type(data).__name__}")

    messages = []
    for item in data:
        agent_id = str(_get(item, "agent_id") or "unknown")
        name = _get(item, "agent_name")
        if name:
            ctx["agent_names"].setdefault(agent_id, str(name))
        label = str(_get(item, "sentiment") or "neutral").lower()
        messages.append({
            "round": _int(_get(item, "round")),
            "agent_id": agent_id,
            "agent_name": ctx["agent_names"].get(agent_id, agent_id),
            "sentiment": label if label in _SENTIMENT_LABELS else "neutral",
            "polarity": _num(_get(item, "polarity")),
            "summary": str(_get(item, "summary") or ""),
        })
    messages.sort(key=lambda m: (m["round"] is None, m["round"] or 0, m["agent_id"]))

    counts = Counter(m["sentiment"] for m in messages)
    by_agent = _group(messages, lambda m: m["agent_id"],
                      lambda k: ctx["agent_names"].get(k, k))
    by_agent.sort(key=lambda g: g["key"])
    by_round = _group([m for m in messages if m["round"] is not None],
                      lambda m: str(m["round"]), lambda k: f"Round {k}")
    by_round.sort(key=lambda g: int(g["key"]))

    return {
        "status": SECTION_OK if messages else SECTION_INSUFFICIENT,
        "error": None if messages else "no messages were analyzed",
        "distribution": {
            "positive": counts.get("positive", 0),
            "negative": counts.get("negative", 0),
            "neutral": counts.get("neutral", 0),
            "total": len(messages),
        },
        "by_agent": by_agent,
        "by_round": by_round,
        "messages": messages,
    }


_FORMATTERS = {
    "opinion": ("opinion_trajectory", _format_opinion),
    "agreement": ("agreement", _format_agreement),
    "influence": ("influence", _format_influence),
    "sentiment": ("sentiment", _format_sentiment),
}


def _format_section(metric: str, raw: RawMetric, ctx: Dict[str, Any]) -> Dict[str, Any]:
    section_name, formatter = _FORMATTERS[metric]
    status, data, error = raw
    if status not in (SECTION_OK, SECTION_INSUFFICIENT) or data is None:
        return empty_section(section_name, status, error)
    try:
        section = formatter(data, ctx)
    except Exception as exc:  # malformed metric output must not break the page
        logger.exception("analytics_format_failed section=%s", section_name)
        return empty_section(section_name, SECTION_ERROR,
                             f"could not read {metric} output ({type(exc).__name__}: {exc})")
    if status == SECTION_INSUFFICIENT and section["status"] == SECTION_OK:
        section["status"] = SECTION_INSUFFICIENT
        section["error"] = error or "metric reported insufficient data"
    return section


# --------------------------------------------------------------------------- #
# 4. Interaction graph data
# --------------------------------------------------------------------------- #

def build_interaction_graph(
    history: Any,
    influence: Optional[Dict[str, Optional[float]]] = None,
    agent_names: Optional[Dict[str, str]] = None,
    known_agents: Iterable[str] = (),
    messages_sent_fallback: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Nodes = agents (size = influence score from Week 4).
    Edges = who messaged whom in Week 3 (weight = number of messages).

    If the messages carry no recipient information, edges fall back to
    co-participation: two agents are linked once for every round in which
    both spoke. edge_basis says which one was used, so the frontend legend
    can be honest about it.
    """
    influence = influence or {}
    agent_names = agent_names or {}
    messages_sent_fallback = messages_sent_fallback or {}

    sent: Counter = Counter()
    directed_edges: Counter = Counter()
    speakers_by_round: Dict[int, set] = defaultdict(set)
    recipients_seen: set = set()

    for message in _history_messages(history):
        sender = _get(message, "agent_id") or _get(message, "sender")
        if not sender:
            continue
        sender = str(sender)
        sent[sender] += 1
        round_no = _int(_get(message, "round"))
        if round_no is not None:
            speakers_by_round[round_no].add(sender)
        for recipient in _recipients(message):
            if recipient != sender:
                directed_edges[(sender, recipient)] += 1
                recipients_seen.add(recipient)

    agents = sorted(set(map(str, known_agents)) | set(sent) | set(influence)
                    | recipients_seen)
    nodes = [{
        "id": agent,
        "label": agent_names.get(agent, agent),
        "influence": influence.get(agent),
        "messages_sent": sent.get(agent) or messages_sent_fallback.get(agent, 0),
    } for agent in agents]

    if directed_edges:
        edge_basis, directed = "messages", True
        edges = [{"source": s, "target": t, "weight": w, "kind": "messages"}
                 for (s, t), w in sorted(directed_edges.items())]
    elif speakers_by_round:
        edge_basis, directed = "co_participation", False
        pairs: Counter = Counter()
        for speakers in speakers_by_round.values():
            for a, b in combinations(sorted(speakers), 2):
                pairs[(a, b)] += 1
        edges = [{"source": a, "target": b, "weight": w, "kind": "co_participation"}
                 for (a, b), w in sorted(pairs.items())]
    else:
        edge_basis, directed, edges = "none", False, []

    if len(nodes) < 2:
        status, error = SECTION_INSUFFICIENT, "fewer than 2 agents"
    elif not edges:
        status = SECTION_INSUFFICIENT
        error = ("no discussion messages available to build edges"
                 if history is None or not _history_messages(history)
                 else "messages have no sender/round information")
    else:
        status, error = SECTION_OK, None

    return {"status": status, "error": error, "edge_basis": edge_basis,
            "directed": directed, "nodes": nodes, "edges": edges}


# --------------------------------------------------------------------------- #
# 5. Public entry points
# --------------------------------------------------------------------------- #

def build_analytics_response(analytics: Any, history: Any = None) -> Dict[str, Any]:
    """Week 4 analytics (either engine) + Week 3 history -> frontend JSON."""
    raw, meta = _read_analytics(analytics)
    ctx: Dict[str, Any] = {
        "agent_names": _history_agent_names(history),
        "influence": {},
        "messages_sent": {},
    }

    # order matters a little: opinion fills agent names used by later sections
    sections = {
        "opinion_trajectory": _format_section("opinion", raw["opinion"], ctx),
        "influence": _format_section("influence", raw["influence"], ctx),
        "agreement": _format_section("agreement", raw["agreement"], ctx),
        "sentiment": _format_section("sentiment", raw["sentiment"], ctx),
    }

    series_agents = [s["agent_id"] for s in sections["opinion_trajectory"]["series"]]
    try:
        sections["interaction_graph"] = build_interaction_graph(
            history,
            influence=ctx["influence"],
            agent_names=ctx["agent_names"],
            known_agents=list(meta["agents"]) + series_agents,
            messages_sent_fallback=ctx["messages_sent"],
        )
    except Exception as exc:
        logger.exception("analytics_graph_failed")
        sections["interaction_graph"] = empty_section(
            "interaction_graph", SECTION_ERROR,
            f"could not build graph ({type(exc).__name__}: {exc})")

    agents = sorted(set(map(str, meta["agents"])) | set(series_agents)
                    | {n["id"] for n in sections["interaction_graph"]["nodes"]})
    rounds = sorted({int(r) for r in meta["rounds"] if _int(r) is not None}
                    | {p["round"] for s in sections["opinion_trajectory"]["series"]
                       for p in s["points"]}
                    | {r["round"] for r in sections["agreement"]["rounds"]})

    response = {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "discussion_id": meta["discussion_id"] or _get(history, "discussion_id"),
        "topic": meta["topic"] or _get(history, "topic"),
        "agents": agents,
        "agent_names": {a: ctx["agent_names"].get(a, a) for a in agents},
        "rounds": rounds,
        "status": {name: sections[name]["status"] for name in SECTION_NAMES},
        **{name: sections[name] for name in SECTION_NAMES},
        "warnings": [str(w) for w in meta["warnings"]],
        "errors": [str(e) for e in meta["errors"]],
    }
    logger.info("analytics_response_built discussion_id=%s status=%s",
                response["discussion_id"], response["status"])
    return response


def analyze_and_format(history: Any,
                       analytics_fn: Optional[Callable[[Any], Any]] = None) -> Dict[str, Any]:
    """
    One call for the API / Streamlit page: run the analytics, then format.

    analytics_fn defaults to engine.run_analytics. Pass
    unified.analyze_discussion to use the other engine instead.
    """
    if analytics_fn is None:
        from .engine import run_analytics as analytics_fn
    return build_analytics_response(analytics_fn(history), history)


__all__ = ["build_analytics_response", "build_interaction_graph", "analyze_and_format"]
