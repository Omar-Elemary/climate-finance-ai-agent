"""Backend error model — stable HTTP contract, no stack-trace leakage."""
from __future__ import annotations

from typing import Any


class BackendError(Exception):
    """Base for expected backend failures (mapped to HTTP by handlers)."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Any | None = None,
    ) -> None:
        super().__init__(message or self.message)
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        if message is not None:
            self.message = message
        self.details = details


class DiscussionNotFoundError(BackendError):
    status_code = 404
    code = "DISCUSSION_NOT_FOUND"

    def __init__(self, discussion_id: str) -> None:
        super().__init__(
            f"Discussion '{discussion_id}' was not found.",
            code=self.code,
            status_code=self.status_code,
            details={"discussion_id": discussion_id},
        )


class InvalidRequestError(BackendError):
    status_code = 400
    code = "INVALID_REQUEST"


class ServiceUnavailableError(BackendError):
    """Upstream dependency (LLM, retrieval, persistence) unavailable."""

    status_code = 503
    code = "SERVICE_UNAVAILABLE"


class AnalyticsUnavailableError(BackendError):
    status_code = 503
    code = "ANALYTICS_UNAVAILABLE"


def error_payload(code: str, message: str, details: Any | None = None) -> dict:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return payload
