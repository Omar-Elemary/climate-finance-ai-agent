import pytest
from src.metrics.influence import calculate_influence, AgentInfluence


def test_influence_insufficient_agents():
    history = {
        "opinions": {
            "Agent_A": [
                {"round": 0, "opinion": 0.5},
                {"round": 1, "opinion": 0.8},
            ]
        }
    }
    result = calculate_influence(history)
    assert "Agent_A" in result
    assert result["Agent_A"].influence_score is None
    assert result["Agent_A"].status == "insufficient_data"


def test_influence_insufficient_rounds():
    history = {
        "opinions": {
            "Agent_A": [{"round": 0, "opinion": 0.8}],
            "Agent_B": [{"round": 0, "opinion": -0.4}],
        }
    }
    result = calculate_influence(history)
    assert result["Agent_A"].status == "insufficient_data"
    assert result["Agent_B"].status == "insufficient_data"
    assert result["Agent_A"].influence_score is None


def test_influence_zero_movement():
    history = {
        "opinions": {
            "Agent_A": [
                {"round": 0, "opinion": 0.5},
                {"round": 1, "opinion": 0.5},
            ],
            "Agent_B": [
                {"round": 0, "opinion": -0.5},
                {"round": 1, "opinion": -0.5},
            ],
        }
    }
    result = calculate_influence(history)
    assert result["Agent_A"].status == "ok"
    assert result["Agent_B"].status == "ok"
    assert result["Agent_A"].influence_score == 0.0
    assert result["Agent_B"].influence_score == 0.0


def test_influence_strong_convergence_to_speaker():
    history = {
        "opinions": {
            "Agent_A": [
                {"round": 0, "opinion": 1.0},
                {"round": 1, "opinion": 1.0},
            ],
            "Agent_B": [
                {"round": 0, "opinion": 0.0},
                {"round": 1, "opinion": 0.9},
            ],
            "Agent_C": [
                {"round": 0, "opinion": -0.5},
                {"round": 1, "opinion": 0.7},
            ],
        }
    }
    result = calculate_influence(history)

    assert result["Agent_A"].status == "ok"
    assert result["Agent_A"].influence_score is not None
    assert result["Agent_A"].influence_score > result["Agent_B"].influence_score
    assert result["Agent_A"].influence_score > result["Agent_C"].influence_score

    total_score = sum(r.influence_score for r in result.values())
    assert pytest.approx(total_score, rel=1e-2) == 1.0


def test_influence_with_message_activity():
    # Only Agent_A spoke in round 0; Agent_B converged towards Agent_A
    history = {
        "opinions": {
            "Agent_A": [{"round": 0, "opinion": 0.8}, {"round": 1, "opinion": 0.8}],
            "Agent_B": [{"round": 0, "opinion": -0.2}, {"round": 1, "opinion": 0.6}],
        },
        "messages": [
            {"sender": "Agent_A", "round": 0, "content": "Compelling climate finance argument."},
        ]
    }
    result = calculate_influence(history)
    assert result["Agent_A"].messages_sent == 1
    assert result["Agent_B"].messages_sent == 0
    assert result["Agent_A"].influence_score > result["Agent_B"].influence_score


def test_influence_to_dict_structure():
    history = {
        "opinions": {
            "Agent_A": [{"round": 0, "opinion": 0.2}, {"round": 1, "opinion": 0.6}],
            "Agent_B": [{"round": 0, "opinion": 0.8}, {"round": 1, "opinion": 0.7}],
        }
    }
    result = calculate_influence(history)
    dict_res = result["Agent_A"].to_dict()
    assert "agent_id" in dict_res
    assert "influence_score" in dict_res
    assert "status" in dict_res
    assert "raw_pull" in dict_res
    assert "messages_sent" in dict_res
    