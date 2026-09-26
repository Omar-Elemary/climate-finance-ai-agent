"""Topics service — reads the backend-owned curated config (no core calls)."""
from __future__ import annotations

from backend.app.core import TOPICS


def list_topics() -> list[dict]:
    return [dict(t) for t in TOPICS]
