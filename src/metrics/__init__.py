"""Opinion + Agreement analytics (Week 4 — Omar's scope).

Independently usable metric modules. The future unified engine consumes them as::

    result.opinion_change = calculate_opinion_change(history)
    result.agreement = calculate_agreement(history)

Only this package's scope is implemented here: no influence, no sentiment,
no reporting, no visualization.
"""

from .agreement import AgreementRound, calculate_agreement
from .opinion import (
    AgentTrajectorySummary,
    OpinionChangeResult,
    StancePoint,
    calculate_opinion_change,
    extract_stance,
)

__all__ = [
    "AgreementRound",
    "AgentTrajectorySummary",
    "OpinionChangeResult",
    "StancePoint",
    "calculate_agreement",
    "calculate_opinion_change",
    "extract_stance",
]
