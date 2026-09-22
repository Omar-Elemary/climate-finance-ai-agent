"""Backend package — Persona 3 (Backend/API), Week 5.

Owns ONLY the HTTP boundary. Consumes Week 1-4 via public interfaces:
  - Week 2/3 core: src.agent, src.personas, src.llm, src.tools,
    src.graph, src.routing, src.orchestration, src.persistence
  - Week 4 analytics: src.analytics.run_analytics (never reimplements metrics)

Ensures repo root is importable so `src.*` resolves whether the app is
launched from the repo root or from backend/.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

__all__ = []
