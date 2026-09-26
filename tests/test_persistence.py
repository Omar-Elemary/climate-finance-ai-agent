"""
Unit tests for the Persistence layer (Task 6/7).

OWNER: Omar Mowena — Persistence / Storage
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from src.persistence import FilePersistence
from src.orchestration.models import (
    DiscussionState,
    DiscussionStatus,
    Message,
    OpinionRecord,
    RetrievalEvent,
)


@pytest.fixture
def temp_store():
    """A FilePersistence instance backed by a temporary directory,
    so tests never touch the real data/discussions folder and never
    leave files behind."""
    temp_dir = tempfile.mkdtemp()
    store = FilePersistence(storage_dir=temp_dir)
    yield store
    shutil.rmtree(temp_dir, ignore_errors=True)


def make_sample_state(discussion_id: str = "run-1") -> DiscussionState:
    state = DiscussionState(
        discussion_id=discussion_id,
        topic="Should developed countries increase climate finance?",
        participants=["cfo_agent_01", "env_specialist_01"],
        current_round=1,
        total_rounds=3,
    )
    state.add_message(Message(
        message_id="m1", discussion_id=discussion_id, round=1,
        agent_id="cfo_agent_01", agent_name="CFO Expert",
        content="From a financial perspective...",
    ))
    state.add_opinion(OpinionRecord(
        agent_id="cfo_agent_01", agent_name="CFO Expert", round=1,
        opinion="STANCE: Support (0.6)",
    ))
    return state


# ----------------------------------------------------------------------
# Task 6: Store Discussion History
# ----------------------------------------------------------------------

def test_save_creates_a_file(temp_store):
    state = make_sample_state()
    temp_store.save(state)
    assert temp_store.exists(state.discussion_id)


def test_load_returns_none_for_unknown_id(temp_store):
    assert temp_store.load("does-not-exist") is None


def test_save_then_load_round_trip(temp_store):
    """Core acceptance test: what goes in must come back out identically."""
    state = make_sample_state()
    temp_store.save(state)

    loaded = temp_store.load(state.discussion_id)

    assert loaded is not None
    assert loaded.discussion_id == state.discussion_id
    assert loaded.topic == state.topic
    assert loaded.participants == state.participants
    assert len(loaded.messages) == 1
    assert loaded.messages[0].content == "From a financial perspective..."


def test_one_row_per_agent_per_round(temp_store):
    """Acceptance test (Task 6): querying the store after a run returns
    one entry per agent per round."""
    state = make_sample_state()

    # Simulate a second agent's turn in the same round
    state.add_message(Message(
        message_id="m2", discussion_id=state.discussion_id, round=1,
        agent_id="env_specialist_01", agent_name="Environmental Specialist",
        content="From an environmental perspective...",
    ))

    temp_store.save(state)
    loaded = temp_store.load(state.discussion_id)

    round_1_messages = loaded.get_messages_for_round(1)
    agent_ids_in_round_1 = {m.agent_id for m in round_1_messages}

    assert len(round_1_messages) == 2
    assert agent_ids_in_round_1 == {"cfo_agent_01", "env_specialist_01"}


def test_retrieval_events_are_persisted(temp_store):
    state = make_sample_state()
    state.add_retrieval_event(RetrievalEvent(
        event_id="e1", discussion_id=state.discussion_id, round=1,
        agent_id="cfo_agent_01", query="climate finance risks",
        results=[{"source_url": "https://example.com", "chunk_text": "..."}],
    ))
    temp_store.save(state)

    loaded = temp_store.load(state.discussion_id)
    assert len(loaded.retrieval_events) == 1
    assert loaded.retrieval_events[0].query == "climate finance risks"


# ----------------------------------------------------------------------
# Task 7: Opinion Evolution & Influence
# ----------------------------------------------------------------------

def test_opinion_snapshots_accumulate_across_rounds(temp_store):
    """Acceptance test (Task 7): opinion history includes at least
    3 rounds' worth of entries per agent."""
    state = make_sample_state()

    for round_number in [2, 3]:
        state.current_round = round_number
        state.add_opinion(OpinionRecord(
            agent_id="cfo_agent_01", agent_name="CFO Expert",
            round=round_number,
            opinion=f"STANCE: Strongly Support (0.{6 + round_number})",
        ))

    temp_store.save(state)
    loaded = temp_store.load(state.discussion_id)

    history = loaded.get_opinion_history("cfo_agent_01")
    assert len(history) == 3
    assert [r.round for r in history] == [1, 2, 3]


def test_repeated_save_overwrites_previous_state(temp_store):
    """save() should reflect the LATEST full state, not append duplicates,
    since it's called again after every round with the growing state."""
    state = make_sample_state()
    temp_store.save(state)

    state.current_round = 2
    state.add_message(Message(
        message_id="m2", discussion_id=state.discussion_id, round=2,
        agent_id="cfo_agent_01", agent_name="CFO Expert",
        content="Round 2 statement...",
    ))
    temp_store.save(state)

    loaded = temp_store.load(state.discussion_id)
    assert loaded.current_round == 2
    assert len(loaded.messages) == 2


# ----------------------------------------------------------------------
# Housekeeping
# ----------------------------------------------------------------------

def test_list_discussion_ids(temp_store):
    temp_store.save(make_sample_state("run-a"))
    temp_store.save(make_sample_state("run-b"))

    ids = temp_store.list_discussion_ids()
    assert set(ids) == {"run-a", "run-b"}


def test_delete_removes_the_file(temp_store):
    state = make_sample_state()
    temp_store.save(state)
    assert temp_store.exists(state.discussion_id)

    temp_store.delete(state.discussion_id)
    assert not temp_store.exists(state.discussion_id)