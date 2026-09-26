"""
tests/test_analytics_engine.py
OWNER: HANAA

Covers contracts.py, validation.py and engine.py only.
No teammate metric module is imported: every metric is injected as a fake
callable, so these tests pass whether or not influence.py / sentiment.py exist.
"""

import json
from dataclasses import dataclass

import pytest

from src.analytics import (
    AnalyticsEngine,
    AnalyticsReport,
    MetricStatus,
    ValidationError,
    run_analytics,
    to_jsonable,
    validate_history,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

def _history(rounds=2, agents=("investor", "policy_expert")):
    opinions, messages = [], []
    for round_no in range(1, rounds + 1):
        for index, agent in enumerate(agents):
            opinions.append({
                "agent_id": agent,
                "round": round_no,
                "stance": 0.5 - 0.1 * index,
                "opinion": f"{agent} position at round {round_no}",
            })
            messages.append({
                "agent_id": agent,
                "round": round_no,
                "content": f"msg {agent} r{round_no}",
                "recipient_id": agents[(index + 1) % len(agents)],
            })
    return {
        "discussion_id": "test-run-001",
        "topic": "Should developed countries increase climate finance?",
        "opinions": opinions,
        "messages": messages,
    }


@pytest.fixture
def history():
    return _history()


@pytest.fixture
def fake_metrics():
    return {
        "opinion": lambda h: {"investor": {"stance": 0.5, "status": "ok"}},
        "agreement": lambda h: {1: 0.9, 2: 0.95},
        "influence": lambda h: {"investor": {"influence_score": 1.0, "status": "ok"}},
        "sentiment": lambda h: {"investor": {"sentiment": 0.2, "status": "ok"}},
    }


class _DiscussionStateLike:
    """Stands in for a Week 3 DiscussionState (dict behind .to_dict())."""

    def __init__(self, payload):
        self._payload = payload

    def to_dict(self):
        return self._payload


# --------------------------------------------------------------------------- #
# validation.py
# --------------------------------------------------------------------------- #

def test_valid_history_passes(history):
    result = validate_history(history)
    assert result.is_valid
    assert result.errors == []
    assert result.summary.n_agents == 2
    assert result.summary.n_rounds == 2
    assert result.summary.n_opinions == 4
    assert result.summary.discussion_id == "test-run-001"


def test_accepts_discussion_state_object(history):
    result = validate_history(_DiscussionStateLike(history))
    assert result.is_valid
    assert result.summary.n_agents == 2


def test_none_history_is_invalid():
    result = validate_history(None)
    assert not result.is_valid
    assert "None" in result.errors[0]


def test_wrong_type_is_invalid():
    result = validate_history("not a discussion")
    assert not result.is_valid


def test_missing_opinions_is_invalid():
    result = validate_history({"messages": [], "topic": "x"})
    assert not result.is_valid
    assert any("opinion" in e for e in result.errors)


def test_strict_mode_raises():
    with pytest.raises(ValidationError):
        validate_history(None, strict=True)


def test_key_aliases_are_normalized():
    result = validate_history({
        "opinion_history": [
            {"agent": "investor", "round_number": "1", "position": "0.4"},
        ],
        "transcript": [{"speaker": "investor", "turn": 1, "text": "hello"}],
    })
    assert result.is_valid
    snapshot = result.history.opinions[0]
    assert snapshot.agent_id == "investor"
    assert snapshot.round == 1
    assert snapshot.stance == pytest.approx(0.4)
    assert result.history.messages[0].agent_id == "investor"


def test_malformed_records_are_warned_not_fatal():
    result = validate_history({
        "opinions": [
            {"agent_id": "a", "round": 1, "stance": 0.2},
            {"round": 2, "stance": 0.3},       # no agent id
            {"agent_id": "a", "stance": 0.4},  # no round
        ]
    })
    assert result.is_valid
    assert len(result.history.opinions) == 1
    assert len(result.warnings) >= 2


def test_single_round_warns():
    result = validate_history(_history(rounds=1))
    assert result.is_valid
    assert any("2 rounds" in w for w in result.warnings)


# --------------------------------------------------------------------------- #
# engine.py
# --------------------------------------------------------------------------- #

def test_engine_runs_all_metrics(history, fake_metrics):
    report = AnalyticsEngine(metric_callables=fake_metrics).run(history)
    assert isinstance(report, AnalyticsReport)
    assert report.is_valid
    assert set(report.metrics) == {"opinion", "agreement", "influence", "sentiment"}
    assert all(r.status is MetricStatus.OK for r in report.metrics.values())
    assert report.agreement == {1: 0.9, 2: 0.95}


def test_missing_metric_module_is_unavailable_not_fatal(history, fake_metrics):
    partial = {k: v for k, v in fake_metrics.items() if k in ("opinion", "agreement")}
    report = AnalyticsEngine(metric_callables=partial).run(history)
    assert report.metrics["opinion"].status is MetricStatus.OK
    # influence/sentiment resolve through the real registry; if a teammate has
    # not written them yet they are unavailable, and if they have they run fine.
    assert report.metrics["influence"].status in (
        MetricStatus.OK, MetricStatus.INSUFFICIENT_DATA,
        MetricStatus.UNAVAILABLE, MetricStatus.ERROR,
    )
    assert report.is_valid


def test_one_metric_raising_does_not_break_the_others(history, fake_metrics):
    def boom(_):
        raise RuntimeError("torch/transformers mismatch")

    fake_metrics["influence"] = boom
    report = AnalyticsEngine(metric_callables=fake_metrics).run(history)
    assert report.metrics["influence"].status is MetricStatus.ERROR
    assert "RuntimeError" in report.metrics["influence"].error
    assert report.metrics["opinion"].status is MetricStatus.OK
    assert report.metrics["sentiment"].status is MetricStatus.OK


def test_strict_mode_propagates_metric_exception(history, fake_metrics):
    fake_metrics["opinion"] = lambda _: (_ for _ in ()).throw(ValueError("bad"))
    engine = AnalyticsEngine(metric_callables=fake_metrics, strict=True)
    with pytest.raises(ValueError):
        engine.run(history)


def test_empty_metric_output_is_insufficient_data(history, fake_metrics):
    fake_metrics["opinion"] = lambda _: {}
    fake_metrics["agreement"] = lambda _: None
    report = AnalyticsEngine(metric_callables=fake_metrics).run(history)
    assert report.metrics["opinion"].status is MetricStatus.INSUFFICIENT_DATA
    assert report.metrics["agreement"].status is MetricStatus.INSUFFICIENT_DATA
    assert report.opinion is None  # .data() only returns OK payloads


def test_metric_self_reported_insufficiency_is_respected(history, fake_metrics):
    fake_metrics["influence"] = lambda _: {
        "investor": {"influence_score": None, "status": "insufficient_data"},
        "cfo": {"influence_score": None, "status": "insufficient_data"},
    }
    report = AnalyticsEngine(metric_callables=fake_metrics).run(history)
    assert report.metrics["influence"].status is MetricStatus.INSUFFICIENT_DATA


def test_invalid_input_yields_report_not_exception(fake_metrics):
    report = AnalyticsEngine(metric_callables=fake_metrics).run(None)
    assert not report.is_valid
    assert report.errors
    assert all(r.status is MetricStatus.UNAVAILABLE for r in report.metrics.values())


def test_metric_subset_is_respected(history, fake_metrics):
    report = AnalyticsEngine(metrics=["opinion"],
                             metric_callables=fake_metrics).run(history)
    assert set(report.metrics) == {"opinion"}


def test_metrics_receive_the_original_history_object(history, fake_metrics):
    seen = {}
    state = _DiscussionStateLike(history)
    fake_metrics["opinion"] = lambda h: seen.setdefault("arg", h) and {}
    AnalyticsEngine(metric_callables=fake_metrics).run(state)
    assert seen["arg"] is state


def test_run_analytics_convenience(history, fake_metrics):
    report = run_analytics(history, metric_callables=fake_metrics)
    assert report.is_valid
    assert report.influence == {"investor": {"influence_score": 1.0, "status": "ok"}}


def test_available_metrics_reports_injected(fake_metrics):
    engine = AnalyticsEngine(metric_callables={"opinion": fake_metrics["opinion"]})
    assert engine.available_metrics()["opinion"] is True


# --------------------------------------------------------------------------- #
# contracts.py / serialization
# --------------------------------------------------------------------------- #

def test_report_is_json_serializable(history, fake_metrics):
    report = AnalyticsEngine(metric_callables=fake_metrics).run(history)
    payload = report.to_dict()
    text = json.dumps(payload)           # must not raise — Ziad dumps this
    assert "schema_version" in text
    assert payload["summary"]["n_agents"] == 2
    assert payload["metrics"]["opinion"]["status"] == "ok"


def test_teammate_dataclasses_are_serialized(history, fake_metrics):
    @dataclass
    class AgentInfluence:
        influence_score: float
        raw_pull: float
        messages_sent: int
        status: str

    fake_metrics["influence"] = lambda _: {
        "investor": AgentInfluence(0.6, 0.12, 3, "ok"),
    }
    report = AnalyticsEngine(metric_callables=fake_metrics).run(history)
    payload = report.to_dict()
    json.dumps(payload)
    assert payload["metrics"]["influence"]["data"]["investor"]["influence_score"] == 0.6


def test_to_jsonable_handles_odd_types():
    class Custom:
        def __init__(self):
            self.value = 1
            self._hidden = 2

    assert to_jsonable(Custom()) == {"value": 1}
    assert to_jsonable({1, 2}) == [1, 2] or sorted(to_jsonable({1, 2})) == [1, 2]
    assert to_jsonable(MetricStatus.OK) == "ok"


def test_statuses_helper(history, fake_metrics):
    report = AnalyticsEngine(metric_callables=fake_metrics).run(history)
    assert report.statuses()["agreement"] == "ok"
    