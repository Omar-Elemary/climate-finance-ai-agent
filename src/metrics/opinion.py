"""Opinion Change Analytics (Week 4).

Converts Week 3 opinion snapshots into numeric stance trajectories.

WEEK 3 INPUT REALITY (see src/orchestration/models.py :: OpinionRecord):
  - agent_id, agent_name, round, opinion (FREE-FORM TEXT), evidence, sources
  - There is NO numeric stance field in Week 3 output.

Therefore stance is derived deterministically from the opinion text:

  1. Count support cues P and oppose cues N (word-boundary regex,
     case-insensitive; overlapping matches resolved longest-first).
  2. A cue preceded within 3 tokens by a negator (not/no/never/without/
     cannot/...) flips polarity ("not bankable" -> oppose).
  3. stance = (P - N) / (P + N); no cues -> 0.0 (neutral, no signal).
  4. If conditional markers are present (conditional/only if/however/...)
     and stance != 0, magnitude is dampened x0.8 (qualified positions).

Range [-1.0, +1.0]: -1 = strongly against, 0 = neutral/no signal,
+1 = strongly in favor (of the discussion topic as framed).

The cue lists are tuned to the climate-finance language used in this repo
(bankable/unbankable, taxonomy, guarantees, additionality, ...). Topic
action verbs (increase/expand/accelerate) are deliberately NOT cues —
every opinion in this corpus is about increasing finance, so they carry
no directional signal.

Limitations:
  - Lexicon scoring is a proxy, not true understanding; sarcasm, complex
    negation scope, and implicit positions are missed.
  - No LLM is used: fully deterministic and reproducible.
  - If Week 3 ever gains a numeric stance field, prefer it over this.

Missing-data behavior (never invents values):
  - empty/non-string opinion      -> stance None, status "missing"
  - out-of-range numeric / bool   -> stance None, status "invalid"
  - (agent, round) absent          -> StancePoint status "missing"
  - >1 snapshot for (agent, round) -> LAST record wins, n_snapshots noted
  - change is computed ONLY between consecutive round numbers with both
    stances valid; otherwise None.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

STANCE_MIN = -1.0
STANCE_MAX = 1.0
CONDITIONAL_DAMPING = 0.8
NEGATION_WINDOW = 3  # tokens

SUPPORT_CUES = [
    "support", "supports", "supported", "supporting",
    "agree", "agrees", "agreed",
    "endorse", "endorses", "endorsed",
    "advocate", "advocates", "advocated",
    "in favor", "in favour",
    "should", "must", "need", "needs", "necessary", "essential",
    "critical", "urgent", "crucial", "vital",
    "yes", "backing", "welcome", "welcomes",
    "bankable", "feasible", "viable", "achievable",
    "unlock", "unlocks", "enable", "enables",
    "workable", "practical", "financeable", "deliverable",
    "approve", "approves", "commit", "commits", "committed",
    "call for", "calls for",
]

OPPOSE_CUES = [
    "oppose", "opposes", "opposed", "opposing",
    "disagree", "disagrees", "disagreed",
    "against", "reject", "rejects", "rejected",
    "should not", "must not", "cannot support", "can not support",
    "not support",
    "concern", "concerns", "concerned", "worrying", "worried",
    "risk", "risks", "risky",
    "unbankable", "unfeasible", "infeasible", "unviable",
    "skeptical", "skepticism", "sceptical", "scepticism",
    "doubt", "doubts", "doubtful",
    "warning", "warn", "warns",
    "greenwash", "greenwashing",
    "block", "blocks", "undermine", "undermines",
    "hinder", "hinders", "burden", "burdensome",
    "costly", "unaffordable", "unrealistic",
]

CONDITIONAL_MARKERS = [
    "conditional", "only if", "provided", "as long as", "however",
    "on condition", "subject to", "contingent", "sunset",
    "unless", "although", "though",
]

NEGATORS = {
    "not", "no", "never", "neither", "nor", "without",
    "hardly", "barely", "cannot", "cant", "wont", "dont",
    "isnt", "arent", "wasnt", "werent", "havent", "hasnt",
    "hadnt", "couldnt", "shouldnt", "wouldnt", "mustnt", "aint",
}

_CUE_PATTERNS: list = []  # (compiled regex, polarity +1/-1), longest first


def _build_cue_patterns() -> list:
    patterns = []
    for cue in SUPPORT_CUES:
        patterns.append(
            (re.compile(r"\b" + re.escape(cue) + r"\b"), 1, len(cue))
        )
    for cue in OPPOSE_CUES:
        patterns.append(
            (re.compile(r"\b" + re.escape(cue) + r"\b"), -1, len(cue))
        )
    patterns.sort(key=lambda p: p[2], reverse=True)  # longest first
    return [(rx, pol) for rx, pol, _ in patterns]


def _normalize(text: str) -> str:
    text = text.lower().replace("n't", " not")
    return re.sub(r"[^a-z\s]", " ", text)


def extract_stance(opinion: Any) -> tuple[float | None, dict]:
    """Map one Week 3 opinion text to a stance in [-1.0, +1.0].

    Returns (stance, detail). stance is None when the opinion is
    missing/empty (detail["status"] == "missing").
    """
    if isinstance(opinion, bool):
        return None, {"status": "invalid", "support": 0, "oppose": 0, "n_cues": 0}
    if isinstance(opinion, (int, float)):
        # Numeric stance supplied directly (future Week 3 field / tests):
        # reuse it instead of deriving from text.
        if STANCE_MIN <= float(opinion) <= STANCE_MAX:
            return round(float(opinion), 3), {
                "status": "ok", "support": 0, "oppose": 0,
                "n_cues": 0, "numeric": True,
            }
        return None, {"status": "invalid", "support": 0, "oppose": 0, "n_cues": 0}
    if not isinstance(opinion, str) or not opinion.strip():
        return None, {"status": "missing", "support": 0, "oppose": 0, "n_cues": 0}

    global _CUE_PATTERNS
    if not _CUE_PATTERNS:
        _CUE_PATTERNS = _build_cue_patterns()

    lowered = opinion.lower()

    # Collect cue matches; resolve overlaps longest-first.
    matches: list = []  # (start, end, polarity)
    for rx, polarity in _CUE_PATTERNS:
        for m in rx.finditer(lowered):
            matches.append((m.start(), m.end(), polarity))
    matches.sort(key=lambda m: (m[0], -(m[1] - m[0])))
    taken: list = []
    for start, end, polarity in matches:
        if any(start < e and end > s for s, e, _ in taken):
            continue
        taken.append((start, end, polarity))

    support = oppose = 0
    for start, end, polarity in taken:
        before = _normalize(lowered[:start]).split()
        window = before[-NEGATION_WINDOW:] if before else []
        if any(tok in NEGATORS for tok in window):
            polarity = -polarity
        if polarity > 0:
            support += 1
        else:
            oppose += 1

    total = support + oppose
    stance = (support - oppose) / total if total else 0.0

    conditional = False
    if stance != 0.0:
        conditional = any(m in lowered for m in CONDITIONAL_MARKERS)
        if conditional:
            stance *= CONDITIONAL_DAMPING

    stance = round(max(STANCE_MIN, min(STANCE_MAX, stance)), 3)
    return stance, {
        "status": "ok",
        "support": support,
        "oppose": oppose,
        "n_cues": total,
        "conditional": conditional,
    }


def is_valid_stance(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and STANCE_MIN <= float(value) <= STANCE_MAX
    )


@dataclass
class StancePoint:
    """One agent's stance at one round."""

    agent_id: str
    agent_name: str
    round: int
    stance: float | None
    change: float | None = None
    status: str = "ok"  # ok | missing | invalid
    n_cues: int = 0
    n_snapshots: int = 1

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "round": self.round,
            "stance": self.stance,
            "change": self.change,
            "status": self.status,
            "n_cues": self.n_cues,
            "n_snapshots": self.n_snapshots,
        }


@dataclass
class AgentTrajectorySummary:
    """Movement statistics over one agent's valid stances."""

    agent_id: str
    agent_name: str
    initial_stance: float | None = None
    final_stance: float | None = None
    total_movement: float | None = None  # final - initial
    largest_movement: float | None = None  # max |change|
    direction: str = "insufficient"  # up | down | flat | mixed | insufficient
    n_valid_rounds: int = 0

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "initial_stance": self.initial_stance,
            "final_stance": self.final_stance,
            "total_movement": self.total_movement,
            "largest_movement": self.largest_movement,
            "direction": self.direction,
            "n_valid_rounds": self.n_valid_rounds,
        }


@dataclass
class OpinionChangeResult:
    """Full opinion-change output: trajectories + per-agent summaries."""

    trajectories: dict[str, list[StancePoint]] = field(default_factory=dict)
    summaries: dict[str, AgentTrajectorySummary] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            agent_id: [p.to_dict() for p in points]
            for agent_id, points in self.trajectories.items()
        }


def _iter_opinion_records(history: Any) -> list:
    """Yield (agent_id, agent_name, round, opinion_text) from Week 3 history.

    Accepts a DiscussionState, its to_dict() plain dict, or an object with
    an ``opinions`` mapping of agent_id -> list of OpinionRecord/dicts.
    """
    opinions = getattr(history, "opinions", None)
    if opinions is None and isinstance(history, dict):
        opinions = history.get("opinions", {})
    if not isinstance(opinions, dict):
        raise TypeError(
            "history must be a DiscussionState or its to_dict() dict "
            "containing an 'opinions' mapping."
        )
    records = []
    for agent_id, snapshots in opinions.items():
        for snap in snapshots or []:
            if isinstance(snap, dict):
                records.append((
                    snap.get("agent_id", agent_id),
                    snap.get("agent_name", agent_id),
                    snap.get("round"),
                    snap.get("opinion"),
                ))
            else:
                records.append((
                    getattr(snap, "agent_id", agent_id),
                    getattr(snap, "agent_name", agent_id),
                    getattr(snap, "round", None),
                    getattr(snap, "opinion", None),
                ))
    return records


def calculate_opinion_change(history: Any) -> OpinionChangeResult:
    """Build per-agent stance trajectories with round-to-round change.

    change = current_stance - previous_stance, computed only for
    consecutive round numbers where both stances are valid; the first
    valid round per agent has change None.
    """
    # Group snapshots by (agent_id, round); LAST snapshot wins on duplicates.
    agents: dict[str, dict] = {}
    for agent_id, agent_name, round_num, opinion in _iter_opinion_records(history):
        if not isinstance(round_num, int) or isinstance(round_num, bool):
            logger.warning("Skipping opinion with invalid round: %r", round_num)
            continue
        key = (str(agent_id), round_num)
        entry = agents.get(key)
        if entry is None:
            agents[key] = {
                "agent_id": str(agent_id),
                "agent_name": str(agent_name),
                "opinion": opinion,
                "n_snapshots": 1,
            }
        else:
            entry["opinion"] = opinion  # last wins, documented
            entry["n_snapshots"] += 1

    # Regroup: agent -> {round -> entry}
    by_agent: dict[str, dict] = {}
    for (agent_id, round_num), entry in agents.items():
        by_agent.setdefault(agent_id, {"name": entry["agent_name"], "rounds": {}})
        by_agent[agent_id]["rounds"][round_num] = entry

    result = OpinionChangeResult()
    for agent_id, info in by_agent.items():
        points: list[StancePoint] = []
        for round_num in sorted(info["rounds"]):
            entry = info["rounds"][round_num]
            stance, detail = extract_stance(entry["opinion"])
            if detail["status"] in ("missing", "invalid"):
                points.append(StancePoint(
                    agent_id=agent_id, agent_name=info["name"],
                    round=round_num, stance=None, change=None,
                    status=detail["status"], n_snapshots=entry["n_snapshots"],
                ))
            else:
                points.append(StancePoint(
                    agent_id=agent_id, agent_name=info["name"],
                    round=round_num, stance=stance, change=None,
                    status="ok", n_cues=detail["n_cues"],
                    n_snapshots=entry["n_snapshots"],
                ))
        # Round-to-round change over consecutive, valid rounds only.
        prev: StancePoint | None = None
        for point in points:
            if (
                prev is not None
                and point.status == "ok"
                and prev.status == "ok"
                and point.round == prev.round + 1
            ):
                point.change = round(point.stance - prev.stance, 3)
            prev = point
        result.trajectories[agent_id] = points
        result.summaries[agent_id] = _summarize(agent_id, info["name"], points)

    return result


def _summarize(agent_id: str, agent_name: str,
               points: list[StancePoint]) -> AgentTrajectorySummary:
    valid = [p for p in points if p.status == "ok" and p.stance is not None]
    summary = AgentTrajectorySummary(agent_id=agent_id, agent_name=agent_name,
                                     n_valid_rounds=len(valid))
    if not valid:
        return summary
    summary.initial_stance = valid[0].stance
    summary.final_stance = valid[-1].stance
    summary.total_movement = round(summary.final_stance - summary.initial_stance, 3)
    changes = [p.change for p in points
               if p.status == "ok" and p.change is not None]
    if changes:
        summary.largest_movement = round(max(abs(c) for c in changes), 3)
        if all(c > 0 for c in changes):
            summary.direction = "up"
        elif all(c < 0 for c in changes):
            summary.direction = "down"
        elif all(c == 0 for c in changes):
            summary.direction = "flat"
        else:
            summary.direction = "mixed"
    return summary
