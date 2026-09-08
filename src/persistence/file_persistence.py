"""
File-based (JSON) implementation of the DiscussionPersistence Protocol.

OWNER: Omar Mowena — Persistence / Storage

Design notes (for the write-up):
- Storage strategy: one JSON file per discussion, named
  `{discussion_id}.json`, containing the FULL serialized DiscussionState
  (not incremental diffs). Each save() call overwrites the file with the
  current complete state.
- Why full-overwrite instead of incremental writes: DiscussionState is
  small enough (a handful of agents x a few rounds) that re-writing the
  whole file each time is simple, always-consistent, and trivially easy
  to reconstruct — no risk of the file being a partial/corrupt sequence
  of appends if the process crashes mid-round.
- run_id / discussion_id: the orchestrator (Omar) generates and owns
  discussion_id; persistence just uses it as the filename/key. No ID
  generation happens in this module.
- Reconstruction: load() fully rebuilds a DiscussionState object (not a
  raw dict) using the helpers in `models.py`, so calling code can use
  `.get_opinion_history(agent_id)` etc. immediately after loading, exactly
  like a freshly-built state from the orchestrator.
- Week 4 interface: callers that just want the clean, stable JSON shape
  (rather than a live DiscussionState object) should call
  `DiscussionResult.from_state(state).to_dict()` on the loaded state —
  that conversion already exists in orchestration/models.py and is not
  duplicated here.

Known limitations (documented per assignment requirement):
- Not safe for concurrent writers to the same discussion_id (last write
  wins, no file locking).
- No querying across discussions (e.g. "all discussions on topic X") —
  Week 4 would need to load() each discussion_id individually, or a
  future version could add an index file.
"""

import json
import logging
from pathlib import Path

from ..orchestration.models import DiscussionState
from .models import discussion_state_from_dict

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = Path("data/discussions")


class FilePersistence:
    """Persists DiscussionState objects as JSON files on disk."""

    def __init__(self, storage_dir: str | Path = DEFAULT_STORAGE_DIR):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, discussion_id: str) -> Path:
        return self.storage_dir / f"{discussion_id}.json"

    def save(self, state: DiscussionState) -> None:
        """Persist the current discussion state (overwrites any previous
        save for the same discussion_id)."""
        path = self._path_for(state.discussion_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(
                "Saved discussion %s (round %d, %d messages) to %s",
                state.discussion_id, state.current_round, len(state.messages), path,
            )
        except Exception as e:
            logger.error("Failed to save discussion %s: %s", state.discussion_id, e)
            raise

    def load(self, discussion_id: str) -> DiscussionState | None:
        """Load and fully reconstruct a DiscussionState by ID.
        Returns None if no saved state exists for that ID."""
        path = self._path_for(discussion_id)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return discussion_state_from_dict(data)
        except Exception as e:
            logger.error("Failed to load discussion %s: %s", discussion_id, e)
            return None

    def exists(self, discussion_id: str) -> bool:
        return self._path_for(discussion_id).exists()

    def list_discussion_ids(self) -> list[str]:
        """List every discussion_id currently persisted to disk."""
        return [p.stem for p in self.storage_dir.glob("*.json")]

    def delete(self, discussion_id: str) -> None:
        path = self._path_for(discussion_id)
        if path.exists():
            path.unlink()