"""
tests/test_analytics_adapter.py
OWNER: HANAA — Week 5

Tests for src/analytics/adapter.py and src/analytics/response_format.py.

Uses the REAL Week 4 metrics (opinion, agreement, influence) so that a change
in a teammate's output shape shows up here as a failing test, before the
frontend sees an empty chart. Sentiment is simulated with rows shaped exactly
like sentiment.get_sentiment_series() — no LLM, no API key, no network.

Run:  python -m pytest tests/test_analytics_adapter.py -v
"""

import json
import pytest

from src.analytics.adapter import (
    analyze_and_format,
    build_analytics_response,
    build_interaction_graph,
)
from src.analytics.engine import AnalyticsEngine
from src.analytics.response_format import (
    EXAMPLE_RESPONSE,
    SECTION_NAMES,
    empty_section,
)

opinion = pytest.importorskip("src.metrics.opinion")
agreement = pytest.importorskip("src.metrics.agreement")
influence = pytest.importorskip("src.metrics.influence")


# --------------------------------------------------------------------------- #
# A discussion shaped like the real Week 3 output (demo run test-run-001)
# --------------------------------------------------------------------------- #

AGENTS = {
    "investor": "Climate Investor",
    "policy_expert": "Policy Expert",
    "scientist": "Environmental Scientist",
    "cfo_agent": "CFO Agent",
}
# Text picked so opinion.extract_stance gives the demo report's stances.
TEXT = {
    "investor": ["We should support this; the pipeline is bankable.",
                 "I am concerned about the risks; this looks costly.",
                 "Let us look at the numbers again."],
    "policy_expert": ["Increased finance is essential and we must commit."] * 3,
    "scientist": ["The evidence says action is urgent and necessary."] * 3,
    "cfo_agent": ["Let us review the balance sheet first.",
                  "I have doubts; the burden on budgets is a risk.",
                  "We will revisit the figures next quarter."],
}
RING = {"investor": "policy_expert", "policy_expert": "scientist",
        "scientist": "cfo_agent", "cfo_agent": "investor"}


def make_history(with_recipients=True):
    opinions = {
        agent: [{"agent_id": agent, "agent_name": name, "round": r,
                 "opinion": TEXT[agent][r], "evidence": [], "sources": []}
                for r in range(3)]
        for agent, name in AGENTS.items()
    }
    messages, n = [], 0
    for r in range(3):
        for agent, name in AGENTS.items():
            n += 1
            message = {"message_id": f"m{n}", "agent_id": agent,
                       "agent_name": name, "round": r, "content": TEXT[agent][r]}
            if with_recipients:
                message["metadata"] = {"recipient_id": RING[agent]}
            messages.append(message)
    return {"discussion_id": "test-run-001",
            "topic": "Should developed countries increase climate finance?",
            "opinions": opinions, "messages": messages}


def sentiment_rows(history):
    """Same shape as sentiment.get_sentiment_series()."""
    tone = {"investor": [("positive", 0.5), ("negative", -0.4), ("neutral", 0.0)],
            "policy_expert": [("positive", 0.6)] * 3,
            "scientist": [("positive", 0.4), ("neutral", 0.1), ("positive", 0.5)],
            "cfo_agent": [("neutral", 0.0), ("negative", -0.5), ("neutral", -0.1)]}
    return [{"message_id": m["message_id"], "agent_id": m["agent_id"],
             "agent_name": m["agent_name"], "round": m["round"],
             "sentiment": tone[m["agent_id"]][m["round"]][0],
             "polarity": tone[m["agent_id"]][m["round"]][1],
             "summary": f"{m['agent_name']} summary.", "content": m["content"]}
            for m in history["messages"]]


@pytest.fixture
def history():
    return make_history()


@pytest.fixture
def unified_objects(history):
    """What unified.py AnalyticsEngine.analyze() returns."""
    return {
        "opinion_change": opinion.calculate_opinion_change(history),
        "agreement": agreement.calculate_agreement(history),
        "influence": influence.calculate_influence(history),
        "sentiment": sentiment_rows(history),
    }


@pytest.fixture
def unified_dicts(unified_objects):
    """What unified.py AnalyticsEngine.analyze_to_dict() returns."""
    return {
        "opinion_change": unified_objects["opinion_change"].to_dict(),
        "agreement": [r.to_dict() for r in unified_objects["agreement"]],
        "influence": {k: v.to_dict() for k, v in unified_objects["influence"].items()},
        "sentiment": unified_objects["sentiment"],
    }


@pytest.fixture
def engine_report(history):
    """What engine.py run_analytics() returns (sentiment injected, no LLM)."""
    engine = AnalyticsEngine(metric_callables={
        "opinion": opinion.calculate_opinion_change,
        "agreement": agreement.calculate_agreement,
        "influence": influence.calculate_influence,
        "sentiment": sentiment_rows,
    })
    return engine.run(history)


def _chart_data(response):
    """The parts the frontend draws — used to compare engines."""
    return {
        "opinion": [(s["agent_id"], s["points"]) for s in response["opinion_trajectory"]["series"]],
        "agreement": response["agreement"]["rounds"],
        "influence": [(r["agent_id"], r["score"]) for r in response["influence"]["agents"]],
        "sentiment": response["sentiment"]["distribution"],
        "edges": response["interaction_graph"]["edges"],
    }


# --------------------------------------------------------------------------- #
# 1. The promise to the frontend
# --------------------------------------------------------------------------- #

def test_response_has_same_keys_as_example(history, unified_objects):
    response = build_analytics_response(unified_objects, history)
    assert set(response) == set(EXAMPLE_RESPONSE)
    for name in SECTION_NAMES:
        assert set(response[name]) == set(EXAMPLE_RESPONSE[name]), name


def test_empty_sections_have_same_keys_as_example():
    for name in SECTION_NAMES:
        assert set(empty_section(name)) == set(EXAMPLE_RESPONSE[name]), name


def test_every_section_has_status_and_error(history, unified_objects):
    response = build_analytics_response(unified_objects, history)
    for name in SECTION_NAMES:
        assert "status" in response[name] and "error" in response[name]
        assert response["status"][name] == response[name]["status"]


def test_response_is_json_serializable(history, unified_objects, engine_report):
    json.dumps(build_analytics_response(unified_objects, history))
    json.dumps(build_analytics_response(engine_report, history))
    json.dumps(EXAMPLE_RESPONSE)


def test_empty_input_still_returns_every_section():
    response = build_analytics_response(None, None)
    assert set(response) == set(EXAMPLE_RESPONSE)
    for name in SECTION_NAMES:
        assert response[name]["status"] != "ok"


def test_unknown_section_name_rejected():
    with pytest.raises(ValueError):
        empty_section("not_a_section")


# --------------------------------------------------------------------------- #
# 2. Both engines give the same charts
# --------------------------------------------------------------------------- #

def test_engine_report_is_accepted(history, engine_report):
    response = build_analytics_response(engine_report, history)
    assert all(status == "ok" for status in response["status"].values())
    assert response["discussion_id"] == "test-run-001"


def test_engine_report_to_dict_is_accepted(history, engine_report):
    from_object = build_analytics_response(engine_report, history)
    from_dict = build_analytics_response(engine_report.to_dict(), history)
    assert _chart_data(from_object) == _chart_data(from_dict)


def test_unified_objects_and_dicts_give_same_charts(history, unified_objects, unified_dicts):
    assert _chart_data(build_analytics_response(unified_objects, history)) == \
           _chart_data(build_analytics_response(unified_dicts, history))


def test_both_engines_give_same_charts(history, engine_report, unified_objects):
    assert _chart_data(build_analytics_response(engine_report, history)) == \
           _chart_data(build_analytics_response(unified_objects, history))


def test_engine_warnings_and_errors_are_passed_through(history, engine_report):
    engine_report.warnings.append("example warning")
    response = build_analytics_response(engine_report, history)
    assert "example warning" in response["warnings"]


# --------------------------------------------------------------------------- #
# 3. Demo run matches the team's Week 4 report (demo_discussion_report.md)
#    If this fails, a teammate's metric output changed — check with them.
# --------------------------------------------------------------------------- #

def test_demo_run_matches_week4_report(history, unified_objects):
    response = build_analytics_response(unified_objects, history)
    stances = {s["agent_id"]: [p["stance"] for p in s["points"]]
               for s in response["opinion_trajectory"]["series"]}
    assert stances["investor"] == [1.0, -1.0, 0.0]
    assert stances["cfo_agent"] == [0.0, -1.0, 0.0]
    assert stances["policy_expert"] == [1.0, 1.0, 1.0]
    assert [r["score"] for r in response["agreement"]["rounds"]] == [0.75, 0.3333, 0.6667]
    assert response["agreement"]["mean"] == pytest.approx(0.5833)
    assert {r["score"] for r in response["influence"]["agents"]} == {0.25}
    assert response["rounds"] == [0, 1, 2]


# --------------------------------------------------------------------------- #
# 4. Each chart section
# --------------------------------------------------------------------------- #

def test_opinion_uses_agent_names_and_sorted_points(history, unified_objects):
    series = build_analytics_response(unified_objects, history)["opinion_trajectory"]["series"]
    names = {s["agent_id"]: s["agent_name"] for s in series}
    assert names["investor"] == "Climate Investor"
    for s in series:
        rounds = [p["round"] for p in s["points"]]
        assert rounds == sorted(rounds)


def test_opinion_summary_fields(history, unified_objects):
    series = build_analytics_response(unified_objects, history)["opinion_trajectory"]["series"]
    investor = next(s for s in series if s["agent_id"] == "investor")
    assert investor["initial"] == 1.0
    assert investor["final"] == 0.0
    assert investor["total_change"] == -1.0
    assert investor["direction"] == "mixed"


def test_opinion_missing_stance_stays_none():
    data = {"investor": [
        {"agent_id": "investor", "round": 0, "stance": 0.5, "status": "ok"},
        {"agent_id": "investor", "round": 1, "stance": None, "status": "missing"},
    ]}
    section = build_analytics_response({"opinion_change": data})["opinion_trajectory"]
    points = section["series"][0]["points"]
    assert points[1]["stance"] is None          # never invented


def test_agreement_maps_agreement_score_field(history, unified_objects):
    rows = build_analytics_response(unified_objects, history)["agreement"]["rounds"]
    assert {"round", "score", "status", "n_valid"} == set(rows[0])
    assert rows[0]["n_valid"] == 4


def test_agreement_insufficient_round_has_no_score():
    data = [{"round": 0, "agreement_score": None, "status": "insufficient_data"},
            {"round": 1, "agreement_score": 0.8, "status": "ok"}]
    section = build_analytics_response({"agreement": data})["agreement"]
    assert section["rounds"][0]["score"] is None
    assert section["final"] == 0.8 and section["mean"] == 0.8


def test_agreement_accepts_plain_round_to_score_dict():
    section = build_analytics_response({"agreement": {2: 0.5, 1: 0.9}})["agreement"]
    assert [r["round"] for r in section["rounds"]] == [1, 2]
    assert section["final"] == 0.5


def test_influence_sorted_highest_first_none_last():
    data = {"a": {"influence_score": 0.2, "status": "ok"},
            "b": {"influence_score": None, "status": "insufficient_data"},
            "c": {"influence_score": 0.8, "status": "ok"}}
    section = build_analytics_response({"influence": data})["influence"]
    assert [r["agent_id"] for r in section["agents"]] == ["c", "a", "b"]
    assert section["all_equal"] is False


def test_influence_all_equal_flag(history, unified_objects):
    section = build_analytics_response(unified_objects, history)["influence"]
    assert section["all_equal"] is True        # demo: every agent 0.25


def test_influence_all_insufficient_is_insufficient():
    data = {"a": {"influence_score": None, "status": "insufficient_data"}}
    section = build_analytics_response({"influence": data})["influence"]
    assert section["status"] == "insufficient_data"


def test_sentiment_distribution_and_groups(history, unified_objects):
    section = build_analytics_response(unified_objects, history)["sentiment"]
    assert section["distribution"] == {"positive": 6, "negative": 2, "neutral": 4, "total": 12}
    by_agent = {g["key"]: g for g in section["by_agent"]}
    assert by_agent["policy_expert"]["mean_polarity"] == 0.6
    assert by_agent["policy_expert"]["label"] == "Policy Expert"
    assert [g["label"] for g in section["by_round"]] == ["Round 0", "Round 1", "Round 2"]
    assert len(section["messages"]) == 12
    assert "content" not in section["messages"][0]   # full text stays in the discussion view


def test_sentiment_unknown_label_counts_as_neutral():
    rows = [{"agent_id": "a", "round": 0, "sentiment": "ecstatic", "polarity": 0.9}]
    section = build_analytics_response({"sentiment": rows})["sentiment"]
    assert section["distribution"]["neutral"] == 1


def test_sentiment_empty_is_insufficient():
    section = build_analytics_response({"sentiment": []})["sentiment"]
    assert section["status"] == "insufficient_data"


# --------------------------------------------------------------------------- #
# 5. Interaction graph
# --------------------------------------------------------------------------- #

def test_graph_edges_from_message_recipients(history, unified_objects):
    graph = build_analytics_response(unified_objects, history)["interaction_graph"]
    assert graph["status"] == "ok"
    assert graph["edge_basis"] == "messages" and graph["directed"] is True
    edges = {(e["source"], e["target"]): e["weight"] for e in graph["edges"]}
    assert edges[("investor", "policy_expert")] == 3


def test_graph_nodes_carry_influence_and_names(history, unified_objects):
    graph = build_analytics_response(unified_objects, history)["interaction_graph"]
    nodes = {n["id"]: n for n in graph["nodes"]}
    assert len(nodes) == 4
    assert nodes["investor"]["label"] == "Climate Investor"
    assert nodes["investor"]["influence"] == 0.25
    assert nodes["investor"]["messages_sent"] == 3


def test_graph_recipient_top_level_and_list():
    history = {"messages": [
        {"agent_id": "a", "round": 0, "recipient_id": "b"},
        {"agent_id": "a", "round": 0, "recipients": ["b", "c"]},
        {"agent_id": "a", "round": 0, "recipient_id": "a"},   # self-message ignored
    ]}
    graph = build_interaction_graph(history)
    edges = {(e["source"], e["target"]): e["weight"] for e in graph["edges"]}
    assert edges == {("a", "b"): 2, ("a", "c"): 1}


def test_graph_falls_back_to_co_participation():
    history = make_history(with_recipients=False)
    graph = build_interaction_graph(history)
    assert graph["status"] == "ok"
    assert graph["edge_basis"] == "co_participation" and graph["directed"] is False
    assert len(graph["edges"]) == 6                 # 4 agents -> 6 pairs
    assert all(e["weight"] == 3 for e in graph["edges"])   # together in 3 rounds


def test_graph_without_history_is_insufficient(unified_objects):
    graph = build_analytics_response(unified_objects, None)["interaction_graph"]
    assert graph["status"] == "insufficient_data"
    assert graph["edges"] == [] and len(graph["nodes"]) == 4   # nodes still known


# --------------------------------------------------------------------------- #
# 6. Failures stay contained
# --------------------------------------------------------------------------- #

def test_broken_metric_output_only_breaks_its_section(history, unified_objects):
    unified_objects["agreement"] = "garbage"
    response = build_analytics_response(unified_objects, history)
    assert response["agreement"]["status"] == "error"
    assert "agreement" in response["agreement"]["error"]
    assert response["opinion_trajectory"]["status"] == "ok"
    assert response["influence"]["status"] == "ok"


def test_unavailable_metric_passes_reason_through(history):
    engine = AnalyticsEngine(metric_callables={
        "opinion": opinion.calculate_opinion_change,
        "agreement": agreement.calculate_agreement,
        "influence": influence.calculate_influence,
    }, metrics=["opinion", "agreement", "influence"])
    response = build_analytics_response(engine.run(history), history)
    assert response["sentiment"]["status"] == "unavailable"
    assert response["sentiment"]["error"]


def test_metric_that_raised_shows_error(history):
    def boom(_):
        raise RuntimeError("LLM provider timeout")
    engine = AnalyticsEngine(metric_callables={
        "opinion": opinion.calculate_opinion_change,
        "agreement": agreement.calculate_agreement,
        "influence": influence.calculate_influence,
        "sentiment": boom,
    })
    response = build_analytics_response(engine.run(history), history)
    assert response["sentiment"]["status"] == "error"
    assert "LLM provider timeout" in response["sentiment"]["error"]
    assert response["agreement"]["status"] == "ok"


def test_missing_key_in_unified_dict_is_unavailable(history, unified_objects):
    del unified_objects["sentiment"]
    response = build_analytics_response(unified_objects, history)
    assert response["sentiment"]["status"] == "unavailable"


def test_unsupported_analytics_type_is_error():
    response = build_analytics_response(42)
    assert all(response[n]["status"] == "error" for n in
               ("opinion_trajectory", "agreement", "influence", "sentiment"))


# --------------------------------------------------------------------------- #
# 7. One-call helper for the API / Streamlit page
# --------------------------------------------------------------------------- #

def test_analyze_and_format_with_injected_engine(history, unified_objects):
    response = analyze_and_format(history, analytics_fn=lambda h: unified_objects)
    assert response["status"]["agreement"] == "ok"
    assert response["topic"] == "Should developed countries increase climate finance?"
