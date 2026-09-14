"""
Unit tests for the Sentiment metric (src/metrics/sentiment.py).

OWNER: Omar Mowena — Sentiment Analytics

These tests mock the LLM entirely — no real API calls, no cost, no
network dependency, and fully deterministic. This tests OUR parsing/
cleaning logic, not the LLM's behavior itself.
"""

import shutil
import tempfile
from unittest.mock import MagicMock

import pytest

from src.metrics.sentiment import (
    _clean_message_content,
    analyze_message_sentiment,
    get_sentiment_series,
    get_opinion_sentiment_series,
)
from src.persistence import FilePersistence
from src.orchestration.models import DiscussionState, Message, OpinionRecord


# ----------------------------------------------------------------------
# _clean_message_content
# ----------------------------------------------------------------------

def test_clean_message_content_strips_tool_call_boilerplate():
    raw = "Let me gather relevant evidence.\n<tool_call>climate_knowledge_search</tool_call>"
    cleaned = _clean_message_content(raw)
    assert cleaned == "Let me gather relevant evidence."
    assert "<tool_call>" not in cleaned


def test_clean_message_content_keeps_original_if_nothing_before_tool_call():
    raw = "<tool_call>climate_knowledge_search</tool_call>"
    cleaned = _clean_message_content(raw)
    # Nothing meaningful before the tool_call -> fall back to original
    assert cleaned == raw


def test_clean_message_content_unchanged_when_no_tool_call():
    raw = "This is a normal message with no tool calls at all."
    assert _clean_message_content(raw) == raw


# ----------------------------------------------------------------------
# analyze_message_sentiment (LLM mocked)
# ----------------------------------------------------------------------

def make_mock_llm(response_text: str):
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_llm.generate.return_value = mock_response
    return mock_llm


def test_analyze_message_sentiment_parses_well_formed_response():
    llm = make_mock_llm(
        "SENTIMENT: positive (0.6)\n"
        "SUMMARY: The agent expressed strong support for the proposal."
    )
    result = analyze_message_sentiment(llm, "Some message content")

    assert result["sentiment"] == "positive"
    assert result["polarity"] == 0.6
    assert "strong support" in result["summary"]


def test_analyze_message_sentiment_handles_negative_polarity():
    llm = make_mock_llm("SENTIMENT: negative (-0.4)\nSUMMARY: Skeptical tone.")
    result = analyze_message_sentiment(llm, "Some message content")

    assert result["sentiment"] == "negative"
    assert result["polarity"] == -0.4


def test_analyze_message_sentiment_falls_back_on_malformed_response():
    """If the LLM doesn't follow the format, we must not crash — return
    a safe neutral default instead."""
    llm = make_mock_llm("I don't understand the question.")
    result = analyze_message_sentiment(llm, "Some message content")

    assert result["sentiment"] == "neutral"
    assert result["polarity"] == 0.0


def test_analyze_message_sentiment_falls_back_on_llm_exception():
    llm = MagicMock()
    llm.generate.side_effect = Exception("API error")

    result = analyze_message_sentiment(llm, "Some message content")

    assert result["sentiment"] == "neutral"
    assert result["polarity"] == 0.0


# ----------------------------------------------------------------------
# get_sentiment_series / get_opinion_sentiment_series (integration, LLM mocked)
# ----------------------------------------------------------------------

@pytest.fixture
def temp_store():
    temp_dir = tempfile.mkdtemp()
    store = FilePersistence(storage_dir=temp_dir)
    yield store
    shutil.rmtree(temp_dir, ignore_errors=True)


def make_state_with_message_and_opinion(discussion_id="test-run"):
    state = DiscussionState(
        discussion_id=discussion_id,
        topic="Test topic",
        participants=["cfo_agent"],
        current_round=1,
        total_rounds=1,
    )
    state.add_message(Message(
        message_id="m1", discussion_id=discussion_id, round=1,
        agent_id="cfo_agent", agent_name="CFO Expert",
        content="Let me think about this carefully.",
    ))
    state.add_opinion(OpinionRecord(
        agent_id="cfo_agent", agent_name="CFO Expert", round=1,
        opinion="This is a strongly positive, well-grounded position.",
    ))
    return state


def test_get_sentiment_series_returns_one_row_per_message(temp_store, monkeypatch):
    state = make_state_with_message_and_opinion()
    temp_store.save(state)

    mock_llm = make_mock_llm("SENTIMENT: neutral (0.0)\nSUMMARY: A cautious statement.")
    monkeypatch.setattr(
        "src.metrics.sentiment.FilePersistence",
        lambda: temp_store,
    )

    series = get_sentiment_series(state.discussion_id, llm=mock_llm)

    assert len(series) == 1
    assert series[0]["agent_id"] == "cfo_agent"
    assert series[0]["round"] == 1
    assert series[0]["sentiment"] == "neutral"


def test_get_opinion_sentiment_series_returns_one_row_per_opinion(temp_store, monkeypatch):
    state = make_state_with_message_and_opinion()
    temp_store.save(state)

    mock_llm = make_mock_llm("SENTIMENT: positive (0.7)\nSUMMARY: Strong support expressed.")
    monkeypatch.setattr(
        "src.metrics.sentiment.FilePersistence",
        lambda: temp_store,
    )

    series = get_opinion_sentiment_series(state.discussion_id, llm=mock_llm)

    assert len(series) == 1
    assert series[0]["agent_id"] == "cfo_agent"
    assert series[0]["sentiment"] == "positive"
    assert series[0]["polarity"] == 0.7


def test_get_sentiment_series_raises_for_unknown_run(temp_store, monkeypatch):
    monkeypatch.setattr(
        "src.metrics.sentiment.FilePersistence",
        lambda: temp_store,
    )
    with pytest.raises(ValueError):
        get_sentiment_series("does-not-exist", llm=MagicMock())