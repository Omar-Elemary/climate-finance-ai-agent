"""Agent Influence Analytics (Week 4).

Estimates correlation-based influence scores for each participating agent,
measuring how much an agent's contributions and stance pull other agents closer
across discussion rounds.

Mathematical Formulation:
  For each transition from round r to r+1:
    1. Active Contribution: Check if Agent A spoke in round r (from messages history).
       If messages are available, A must have participated in round r to exert influence.
    2. Convergence Pull: If Agent A holds stance S_A(r), and Target Agent B holds stance S_B(r),
       the convergence pull towards A is:
           Pull(A -> B, r) = |S_B(r) - S_A(r)| - |S_B(r+1) - S_A(r)|
       A positive value indicates that Agent B shifted closer to Agent A's position.
    3. Message Weighting: Pull is weighted by the relative volume of Agent A's contributions in round r.

  Final scores are normalized across all agents: sum(influence_scores) == 1.0.

Edge Cases:
  - Fewer than 2 distinct agents -> status "insufficient_data", score None.
  - Fewer than 2 rounds -> status "insufficient_data", score None.
  - Zero movement across all rounds -> status "ok", score 0.0 for all agents.
  - Missing or invalid stance records -> cleanly skipped.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .opinion import extract_stance, is_valid_stance

logger = logging.getLogger(__name__)


@dataclass
class AgentInfluence:
    """Influence result for a single agent."""

    agent_id: str
    influence_score: float | None
    raw_pull: float | None = None
    messages_sent: int = 0
    status: str = "ok"  # ok | insufficient_data

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "influence_score": self.influence_score,
            "raw_pull": self.raw_pull,
            "messages_sent": self.messages_sent,
            "status": self.status,
        }


def _extract_stance_trajectories(history: Any) -> dict[str, dict[int, float]]:
    """Extract valid stances per agent across rounds: {agent_id: {round: stance}}."""
    opinions = getattr(history, "opinions", None)
    if opinions is None and isinstance(history, dict):
        opinions = history.get("opinions", {})

    if not isinstance(opinions, dict):
        raise TypeError(
            "history must be a DiscussionState or its to_dict() dict "
            "containing an 'opinions' mapping."
        )

    trajectories: dict[str, dict[int, float]] = {}

    for agent_id, snapshots in opinions.items():
        agent_key = str(agent_id)
        if agent_key not in trajectories:
            trajectories[agent_key] = {}

        for snap in snapshots or []:
            if isinstance(snap, dict):
                r = snap.get("round")
                raw_op = snap.get("opinion")
            else:
                r = getattr(snap, "round", None)
                raw_op = getattr(snap, "opinion", None)

            if not isinstance(r, int) or isinstance(r, bool):
                continue

            stance, detail = extract_stance(raw_op)
            if detail.get("status") == "ok" and is_valid_stance(stance):
                # Last snapshot wins on duplicate (agent, round)
                trajectories[agent_key][r] = float(stance)

    return trajectories


def _extract_message_activity(history: Any) -> tuple[dict[int, dict[str, int]], dict[str, int]]:
    """Extract message counts per round per agent: (round_activity, total_messages)."""
    messages = getattr(history, "messages", None)
    if messages is None and isinstance(history, dict):
        messages = history.get("messages", [])

    round_activity: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_messages: dict[str, int] = defaultdict(int)

    if not isinstance(messages, list):
        return round_activity, total_messages

    for msg in messages:
        sender = None
        round_num = None
        if isinstance(msg, dict):
            sender = msg.get("sender") or msg.get("agent_id")
            round_num = msg.get("round")
        else:
            sender = getattr(msg, "sender", None) or getattr(msg, "agent_id", None)
            round_num = getattr(msg, "round", None)

        if sender is not None:
            sender_str = str(sender)
            total_messages[sender_str] += 1
            if isinstance(round_num, int) and not isinstance(round_num, bool):
                round_activity[round_num][sender_str] += 1

    return round_activity, total_messages


def calculate_influence(history: Any) -> dict[str, AgentInfluence]:
    """Calculate normalized influence scores for all participating agents."""
    trajectories = _extract_stance_trajectories(history)
    agents = sorted(trajectories.keys())

    # Insufficient Data: Less than 2 agents
    if len(agents) < 2:
        return {
            a: AgentInfluence(agent_id=a, influence_score=None, status="insufficient_data")
            for a in agents
        }

    all_rounds: set[int] = set()
    for rounds_dict in trajectories.values():
        all_rounds.update(rounds_dict.keys())
    sorted_rounds = sorted(all_rounds)

    # Insufficient Data: Less than 2 rounds
    if len(sorted_rounds) < 2:
        return {
            a: AgentInfluence(agent_id=a, influence_score=None, status="insufficient_data")
            for a in agents
        }

    round_activity, total_messages = _extract_message_activity(history)
    raw_pulls: dict[str, list[float]] = {a: [] for a in agents}
    total_movement_detected = False

    for idx in range(len(sorted_rounds) - 1):
        r_curr = sorted_rounds[idx]
        r_next = sorted_rounds[idx + 1]

        active_speakers_in_round = round_activity.get(r_curr, {})

        for speaker in agents:
            if r_curr not in trajectories[speaker]:
                continue
            s_speaker = trajectories[speaker][r_curr]

            # If messages exist for this round, check if speaker actively contributed
            if active_speakers_in_round and speaker not in active_speakers_in_round:
                continue

            speaker_round_pulls = []
            for target in agents:
                if target == speaker:
                    continue
                if r_curr in trajectories[target] and r_next in trajectories[target]:
                    s_target_curr = trajectories[target][r_curr]
                    s_target_next = trajectories[target][r_next]

                    if abs(s_target_next - s_target_curr) > 1e-6:
                        total_movement_detected = True

                    dist_before = abs(s_target_curr - s_speaker)
                    dist_after = abs(s_target_next - s_speaker)

                    # Convergence toward speaker
                    pull = dist_before - dist_after
                    speaker_round_pulls.append(pull)

            if speaker_round_pulls:
                avg_pull = sum(speaker_round_pulls) / len(speaker_round_pulls)
                raw_pulls[speaker].append(avg_pull)

    # If agents were completely static across all rounds
    if not total_movement_detected:
        return {
            a: AgentInfluence(
                agent_id=a,
                influence_score=0.0,
                raw_pull=0.0,
                messages_sent=total_messages.get(a, 0),
                status="ok",
            )
            for a in agents
        }

    aggregated_pulls: dict[str, float] = {}
    for a in agents:
        pull_list = raw_pulls[a]
        if not pull_list:
            aggregated_pulls[a] = 0.0
        else:
            avg_pull = sum(pull_list) / len(pull_list)
            aggregated_pulls[a] = max(0.0, avg_pull)

    sum_pulls = sum(aggregated_pulls.values())
    results: dict[str, AgentInfluence] = {}

    for a in agents:
        raw_val = aggregated_pulls[a]
        if sum_pulls > 1e-6:
            score = round(raw_val / sum_pulls, 4)
        else:
            score = round(1.0 / len(agents), 4)

        results[a] = AgentInfluence(
            agent_id=a,
            influence_score=score,
            raw_pull=round(raw_val, 4),
            messages_sent=total_messages.get(a, 0),
            status="ok",
        )

    return results
