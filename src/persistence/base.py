"""
Persistence Protocol (re-exported).

The canonical DiscussionPersistence Protocol is defined in
`src/orchestration/persistence.py` (owned by Omar, read-only for other
members). We import and re-export it here so this module is the single
place other code imports from when it needs the persistence interface —
without duplicating the Protocol definition or touching orchestration/.
"""

from ..orchestration.persistence import DiscussionPersistence, InMemoryPersistence

__all__ = ["DiscussionPersistence", "InMemoryPersistence"]