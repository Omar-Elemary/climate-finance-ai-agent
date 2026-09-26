"""Tests for Opinion Change Analytics (Week 4)."""

import pytest

from src.metrics.opinion import (
    calculate_opinion_change,
    extract_stance,
    is_valid_stance,
)
from src.orchestration.models import (
    DiscussionState,
    DiscussionStatus,
    OpinionRecord,
)


def _rec(agent_id, name, rnd, opinion):
    return {
        "agent_id": agent_id,
        "agent_name": name,
        "round": rnd,
        "opinion": opinion,
    }


# --- stance extraction ---

def test_extract_supportive_text():
    stance, detail = extract_stance(
        "Yes, developed countries should significantly increase climate finance."
    )
    assert stance == 1.0  # yes + should; 'increase' is not a cue
    assert detail["status"] == "ok"
    assert detail["n_cues"] == 2


def test_extract_opposing_text():
    stance, detail = extract_stance("This is unbankable and too costly, we oppose it.")
    assert stance == -1.0
    assert detail["n_cues"] == 3


def test_extract_neutral_no_signal():
    stance, detail = extract_stance("The proposal is noted.")
    assert stance == 0.0
    assert detail["status"] == "ok"
    assert detail["n_cues"] == 0


def test_extract_negation_flips_polarity():
    stance, _ = extract_stance("Solar is not bankable without subsidies.")
    assert stance == -1.0


def test_extract_conditional_dampens():
    stance, detail = extract_stance(
        "Conditional yes: guarantees are acceptable only if thresholds stay binding."
    )
    assert stance == pytest.approx(0.8)  # 1.0 x 0.8 damping
    assert detail["conditional"] is True


def test_extract_numeric_passthrough():
    stance, detail = extract_stance(0.72)
    assert stance == 0.72
    assert detail["status"] == "ok"


def test_extract_invalid_numeric():
    stance, detail = extract_stance(5.0)
    assert stance is None
    assert detail["status"] == "invalid"


def test_extract_missing():
    for bad in ("", "   ", None):
        stance, detail = extract_stance(bad)
        assert stance is None
        assert detail["status"] == "missing"


def test_is_valid_stance():
    assert is_valid_stance(0.0) and is_valid_stance(-1.0) and is_valid_stance(1.0)
    assert not is_valid_stance(1.5) and not is_valid_stance(True)


# --- trajectories ---

def test_negative_movement_and_summary():
    history = {"opinions": {"agent_a": [
        _rec("agent_a", "A", 0, 0.72),
        _rec("agent_a", "A", 1, 0.64),
        _rec("agent_a", "A", 2, 0.51),
    ]}}
    result = calculate_opinion_change(history)
    pts = result.trajectories["agent_a"]
    assert [p.round for p in pts] == [0, 1, 2]
    assert pts[0].change is None  # first round has no change
    assert pts[1].change == pytest.approx(-0.08)
    assert pts[2].change == pytest.approx(-0.13)
    s = result.summaries["agent_a"]
    assert s.initial_stance == pytest.approx(0.72)
    assert s.final_stance == pytest.approx(0.51)
    assert s.total_movement == pytest.approx(-0.21)
    assert s.largest_movement == pytest.approx(0.13)
    assert s.direction == "down"


def test_positive_movement():
    history = {"opinions": {"agent_b": [
        _rec("agent_b", "B", 0, -0.30),
        _rec("agent_b", "B", 1, -0.12),
        _rec("agent_b", "B", 2, 0.05),
    ]}}
    result = calculate_opinion_change(history)
    pts = result.trajectories["agent_b"]
    assert pts[1].change == pytest.approx(0.18)
    assert pts[2].change == pytest.approx(0.17)
    assert result.summaries["agent_b"].direction == "up"
    assert result.summaries["agent_b"].total_movement == pytest.approx(0.35)


def test_zero_movement_flat():
    history = {"opinions": {"a": [_rec("a", "A", 1, 0.5), _rec("a", "A", 2, 0.5)]}}
    result = calculate_opinion_change(history)
    assert result.trajectories["a"][1].change == pytest.approx(0.0)
    assert result.summaries["a"].direction == "flat"


def test_multiple_agents_text_opinions():
    history = {"opinions": {
        "investor": [_rec("investor", "Investor", 1, "Bankability first: we support blended finance.")],
        "cfo": [_rec("cfo", "CFO", 1, "CAPEX makes this unbankable, we oppose merchant risk.")],
    }}
    result = calculate_opinion_change(history)
    assert set(result.trajectories) == {"investor", "cfo"}
    assert result.trajectories["investor"][0].stance == 1.0
    assert result.trajectories["cfo"][0].stance == -1.0


def test_missing_stance_and_gap_breaks_change():
    history = {"opinions": {"a": [
        _rec("a", "A", 0, 0.7),
        _rec("a", "A", 1, ""),      # missing
        _rec("a", "A", 2, 0.5),     # gap from last valid -> change None
    ]}}
    result = calculate_opinion_change(history)
    pts = result.trajectories["a"]
    assert pts[1].status == "missing" and pts[1].stance is None
    assert pts[2].change is None
    s = result.summaries["a"]
    assert s.n_valid_rounds == 2
    assert s.initial_stance == pytest.approx(0.7)


def test_invalid_stance_marked():
    history = {"opinions": {"a": [_rec("a", "A", 1, 5.0)]}}
    result = calculate_opinion_change(history)
    assert result.trajectories["a"][0].status == "invalid"
    assert result.summaries["a"].direction == "insufficient"


def test_duplicate_snapshot_last_wins():
    history = {"opinions": {"a": [
        _rec("a", "A", 1, 0.1),
        _rec("a", "A", 1, 0.9),
    ]}}
    result = calculate_opinion_change(history)
    pts = result.trajectories["a"]
    assert len(pts) == 1
    assert pts[0].stance == pytest.approx(0.9)
    assert pts[0].n_snapshots == 2


def test_accepts_discussion_state_object():
    state = DiscussionState(
        discussion_id="d", topic="t", status=DiscussionStatus.COMPLETED,
    )
    state.add_opinion(OpinionRecord(
        agent_id="a", agent_name="A", round=1, opinion="We support this.",
    ))
    result = calculate_opinion_change(state)
    assert result.trajectories["a"][0].stance == 1.0


def test_to_dict_shape():
    history = {"opinions": {"a": [_rec("a", "A", 0, 0.7), _rec("a", "A", 1, 0.5)]}}
    d = calculate_opinion_change(history).to_dict()
    assert d["a"][0] == {
        "agent_id": "a", "agent_name": "A", "round": 0,
        "stance": 0.7, "change": None, "status": "ok",
        "n_cues": 0, "n_snapshots": 1,
    }
    assert d["a"][1]["change"] == pytest.approx(-0.2)
