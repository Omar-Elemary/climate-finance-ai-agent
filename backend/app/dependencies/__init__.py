"""FastAPI dependency injection — singletons overridable in tests.

Tests replace these via app.dependency_overrides so no real LLM is needed.
"""
from __future__ import annotations

from functools import lru_cache

from backend.app.services.analytics_service import AnalyticsService
from backend.app.services.discussion_service import DiscussionService
from backend.app.services.topics_service import list_topics


@lru_cache(maxsize=1)
def _discussion_service_singleton() -> DiscussionService:
    return DiscussionService()


def get_discussion_service() -> DiscussionService:
    return _discussion_service_singleton()


def get_analytics_service() -> AnalyticsService:
    return AnalyticsService(get_discussion_service())


def get_topics() -> list[dict]:
    return list_topics()


def reset_singletons() -> None:
    _discussion_service_singleton.cache_clear()
