"""Tests for Agreement / Disagreement Analytics (Week 4)."""

import pytest

from src.metrics.agreement import calculate_agreement


def _rec(agent_id, rnd, opinion):
    return {"agent_id": agent_id, "agent_name": agent_id, "round": rnd, "opinion": opinion}


def test_identical_stances_full_agreement():
    history = {"opinions": {
        "a": [_rec("a", 0, 0.5)],
        "b": [_rec("b", 0, 0.5)],
        "c": [_rec("c", 0, 0.5)],
    }}
    (res,) = calculate_agreement(history)
    assert res.round == 0
    assert res.agreement_score == 1.0
    assert res.mean_pairwise_difference == pytest.approx(0.0)
    assert res.status == "ok" and res.n_valid == 3


def test_maximum_disagreement():
    history = {"opinions": {"a": [_rec("a", 0, -1.0)], "b": [_rec("b", 0, 1.0)]}}
    (res,) = calculate_agreement(history)
    assert res.mean_pairwise_difference == pytest.approx(2.0)
    assert res.agreement_score == pytest.approx(0.0)


def test_partial_disagreement_math():
    # diffs: .4, .2, .2 -> mean .2667 -> agreement 1-.1333 = .8667
    history = {"opinions": {
        "a": [_rec("a", 1, 0.8)],
        "b": [_rec("b", 1, 0.4)],
        "c": [_rec("c", 1, 0.6)],
    }}
    (res,) = calculate_agreement(history)
    assert res.mean_pairwise_difference == pytest.approx(0.2667, abs=1e-3)
    assert res.agreement_score == pytest.approx(0.8667, abs=1e-3)


def test_one_agent_insufficient_not_one():
    history = {"opinions": {"a": [_rec("a", 0, 0.9)]}}
    (res,) = calculate_agreement(history)
    assert res.status == "insufficient_data"
    assert res.agreement_score is None  # must NOT pretend agreement = 1


def test_zero_agents_no_rounds():
    assert calculate_agreement({"opinions": {}}) == []


def test_missing_stance_excluded():
    history = {"opinions": {
        "a": [_rec("a", 0, 0.8)],
        "b": [_rec("b", 0, "")],  # missing -> only 1 valid left
    }}
    (res,) = calculate_agreement(history)
    assert res.status == "insufficient_data"
    assert res.agreement_score is None
    assert res.n_valid == 1 and res.n_invalid == 1


def test_invalid_stance_excluded():
    history = {"opinions": {
        "a": [_rec("a", 0, 0.8)],
        "b": [_rec("b", 0, 5.0)],  # out of range
    }}
    (res,) = calculate_agreement(history)
    assert res.status == "insufficient_data"
    assert res.n_invalid == 1


def test_one_result_per_round():
    history = {"opinions": {
        "a": [_rec("a", 0, 0.7), _rec("a", 1, 0.9), _rec("a", 2, -0.8)],
        "b": [_rec("b", 0, 0.65), _rec("b", 1, -0.8), _rec("b", 2, 0.1)],
        "c": [_rec("c", 0, 0.72), _rec("c", 1, 0.1), _rec("c", 2, 0.2)],
    }}
    results = calculate_agreement(history)
    assert [r.round for r in results] == [0, 1, 2]
    assert results[0].agreement_score > results[1].agreement_score  # convergence lost


def test_text_opinions_end_to_end():
    history = {"opinions": {
        "x": [_rec("x", 1, "We fully support this proposal.")],
        "y": [_rec("y", 1, "We strongly support this proposal.")],
    }}
    (res,) = calculate_agreement(history)
    assert res.agreement_score == 1.0  # both extract to +1.0


def test_duplicate_snapshot_last_wins():
    history = {"opinions": {
        "a": [_rec("a", 0, 1.0), _rec("a", 0, -1.0)],  # last = -1.0
        "b": [_rec("b", 0, -1.0)],
    }}
    (res,) = calculate_agreement(history)
    assert res.agreement_score == 1.0


def test_to_dict_shape():
    history = {"opinions": {"a": [_rec("a", 0, 0.0)], "b": [_rec("b", 0, 0.0)]}}
    d = calculate_agreement(history)[0].to_dict()
    assert d == {
        "round": 0, "agreement_score": 1.0, "mean_pairwise_difference": 0.0,
        "n_agents": 2, "n_valid": 2, "n_invalid": 0, "status": "ok",
    }
