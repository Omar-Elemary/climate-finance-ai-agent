"""Agreement / Disagreement Analytics (Week 4).

Exactly ONE agreement score per available discussion round, derived from
the per-agent stances produced by opinion.extract_stance.

Formula (per round):
  1. Collect all VALID stances (in [-1.0, +1.0]; invalid/missing excluded).
  2. mean_difference = mean over unique pairs of |stance_i - stance_j|.
  3. agreement = 1 - (mean_difference / 2), clamped to [0, 1].
     Max possible absolute difference on [-1, +1] is 2, hence /2.

Interpretation: 1.0 = maximum agreement, 0.0 = maximum disagreement.

Edge cases (never fabricate):
  - 0 valid stances  -> status "insufficient_data", score None
  - 1 valid stance   -> status "insufficient_data", score None
                        (NOT 1.0: agreement is undefined for one agent)
  - identical stances -> 1.0
  - duplicate snapshots for (agent, round) -> last wins (shared with opinion)
  - rounds with no opinions are not emitted at all.

Agreement quality is bounded by stance-extraction quality (see opinion.py).
"""

import itertools
import logging
from dataclasses import dataclass, field
from typing import Any

from .opinion import STANCE_MAX, STANCE_MIN, extract_stance, is_valid_stance

logger = logging.getLogger(__name__)

MAX_DIFFERENCE = STANCE_MAX - STANCE_MIN  # 2.0 for [-1, +1]


@dataclass
class AgreementRound:
    """Agreement result for a single round."""

    round: int
    agreement_score: float | None
    mean_pairwise_difference: float | None = None
    n_agents: int = 0
    n_valid: int = 0
    n_invalid: int = 0
    status: str = "ok"  # ok | insufficient_data

    def to_dict(self) -> dict:
        return {
            "round": self.round,
            "agreement_score": self.agreement_score,
            "mean_pairwise_difference": self.mean_pairwise_difference,
            "n_agents": self.n_agents,
            "n_valid": self.n_valid,
            "n_invalid": self.n_invalid,
            "status": self.status,
        }


def _iter_opinion_records(history: Any) -> list:
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
                    snap.get("round"),
                    snap.get("opinion"),
                ))
            else:
                records.append((
                    getattr(snap, "agent_id", agent_id),
                    getattr(snap, "round", None),
                    getattr(snap, "opinion", None),
                ))
    return records


def _stance_from_record(opinion: Any) -> tuple[float | None, str]:
    """Return (stance, validity) where validity is valid|missing|invalid."""
    stance, detail = extract_stance(opinion)
    status = detail["status"]
    if status == "ok" and is_valid_stance(stance):
        return stance, "valid"
    if status == "invalid":
        return None, "invalid"
    return None, "missing"


def calculate_agreement(history: Any) -> list[AgreementRound]:
    """Compute one AgreementRound per round present in Week 3 opinions."""
    # (agent_id, round) -> opinion; LAST snapshot wins on duplicates.
    latest: dict[tuple, Any] = {}
    for agent_id, round_num, opinion in _iter_opinion_records(history):
        if not isinstance(round_num, int) or isinstance(round_num, bool):
            logger.warning("Skipping opinion with invalid round: %r", round_num)
            continue
        latest[(str(agent_id), round_num)] = opinion

    by_round: dict[int, dict[str, Any]] = {}
    for (agent_id, round_num), opinion in latest.items():
        by_round.setdefault(round_num, {})[agent_id] = opinion

    results: list[AgreementRound] = []
    for round_num in sorted(by_round):
        stances: list[float] = []
        n_invalid = 0
        for opinion in by_round[round_num].values():
            stance, validity = _stance_from_record(opinion)
            if validity == "valid":
                stances.append(stance)
            else:
                n_invalid += 1
        n_agents = len(by_round[round_num])

        if len(stances) < 2:
            results.append(AgreementRound(
                round=round_num, agreement_score=None,
                mean_pairwise_difference=None,
                n_agents=n_agents, n_valid=len(stances),
                n_invalid=n_invalid, status="insufficient_data",
            ))
            continue

        diffs = [abs(a - b) for a, b in itertools.combinations(stances, 2)]
        mean_diff = sum(diffs) / len(diffs)
        score = max(0.0, min(1.0, 1.0 - mean_diff / MAX_DIFFERENCE))
        results.append(AgreementRound(
            round=round_num, agreement_score=round(score, 4),
            mean_pairwise_difference=round(mean_diff, 4),
            n_agents=n_agents, n_valid=len(stances),
            n_invalid=n_invalid, status="ok",
        ))

    return results
