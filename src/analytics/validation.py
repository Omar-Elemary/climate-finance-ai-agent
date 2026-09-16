"""
src/analytics/validation.py
OWNER: HANAA

Input contract check for the analytics layer.

Accepts anything Week 3 can hand us:
  * a DiscussionState object (has .to_dict())
  * the dict loaded from data/discussions/<id>.json
  * a plain dict assembled by hand in tests

and answers three questions:
  1. Is this usable at all?                  -> ValidationResult.is_valid
  2. What's wrong / suspicious?              -> .errors / .warnings
  3. What does it contain?                   -> .history (NormalizedHistory)

No metric logic here. Validation never mutates the caller's object.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .contracts import (
    DiscussionSummary,
    MessageRecord,
    NormalizedHistory,
    OpinionSnapshot,
)

# Key aliases — Week 3 / teammates spell these slightly differently.
_AGENT_KEYS = ("agent_id", "agent", "speaker", "speaker_id", "sender_id",
               "from_agent", "author")
_ROUND_KEYS = ("round", "round_number", "round_index", "round_id", "turn")
_STANCE_KEYS = ("stance", "stance_value", "score", "position")
_OPINION_TEXT_KEYS = ("opinion", "text", "content", "opinion_text", "statement")
_RECIPIENT_KEYS = ("recipient_id", "to_agent", "recipient", "target_id")

_OPINIONS_CONTAINER_KEYS = ("opinions", "opinion_history", "opinion_records",
                            "records", "snapshots")
_MESSAGES_CONTAINER_KEYS = ("messages", "transcript", "message_history", "history")


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    history: Optional[NormalizedHistory] = None

    @property
    def summary(self) -> DiscussionSummary:
        return self.history.summary if self.history else DiscussionSummary()


class ValidationError(ValueError):
    """Raised by validate_history(..., strict=True) when the input is unusable."""


# --------------------------------------------------------------------------- #
# Small coercion helpers
# --------------------------------------------------------------------------- #

def _first(mapping: Dict[str, Any], keys) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _as_dict(obj: Any) -> Optional[Dict[str, Any]]:
    """Best-effort conversion of an arbitrary record into a plain dict."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        try:
            result = obj.to_dict()
            if isinstance(result, dict):
                return result
        except Exception:
            return None
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
    return None


def _as_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and float(value).is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def coerce_history(history: Any) -> Optional[Dict[str, Any]]:
    """DiscussionState | dict | object -> plain dict (or None if impossible)."""
    return _as_dict(history)


def _collect(container: Any, keys) -> List[Any]:
    """Pull a list of records out of a dict under any of `keys`.

    Tolerates the nested shape {round_1: [...], round_2: [...]} as well as a
    flat list.
    """
    raw = _first(container, keys) if isinstance(container, dict) else None
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        flattened: List[Any] = []
        for key, value in raw.items():
            if isinstance(value, list):
                for item in value:
                    item_dict = _as_dict(item)
                    if item_dict is not None and _first(item_dict, _ROUND_KEYS) is None:
                        item_dict = {**item_dict, "round": key}
                        flattened.append(item_dict)
                    else:
                        flattened.append(item)
            else:
                flattened.append(value)
        return flattened
    return []


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def validate_history(history: Any, *, strict: bool = False) -> ValidationResult:
    """
    Check and normalize a discussion history.

    Returns a ValidationResult. With strict=True, raises ValidationError
    instead of returning is_valid=False.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if history is None:
        return _fail(["history is None"], strict)

    as_dict = coerce_history(history)
    if as_dict is None:
        return _fail(
            [f"history must be a dict or expose to_dict(); got {type(history).__name__}"],
            strict,
        )

    raw_opinions = _collect(as_dict, _OPINIONS_CONTAINER_KEYS)
    raw_messages = _collect(as_dict, _MESSAGES_CONTAINER_KEYS)

    if not raw_opinions:
        errors.append(
            "history has no opinion records (expected one of: "
            + ", ".join(_OPINIONS_CONTAINER_KEYS) + ")"
        )
    if not raw_messages:
        warnings.append(
            "history has no messages; influence/sentiment may report insufficient_data"
        )

    opinions: List[OpinionSnapshot] = []
    for index, record in enumerate(raw_opinions):
        record_dict = _as_dict(record)
        if record_dict is None:
            warnings.append(f"opinions[{index}] is not a record; skipped")
            continue
        agent_id = _first(record_dict, _AGENT_KEYS)
        round_no = _as_int(_first(record_dict, _ROUND_KEYS))
        if agent_id is None:
            warnings.append(f"opinions[{index}] has no agent id; skipped")
            continue
        if round_no is None:
            warnings.append(f"opinions[{index}] has no usable round number; skipped")
            continue
        opinions.append(
            OpinionSnapshot(
                agent_id=str(agent_id),
                round=round_no,
                stance=_as_float(_first(record_dict, _STANCE_KEYS)),
                opinion=_first(record_dict, _OPINION_TEXT_KEYS),
                raw=record_dict,
            )
        )

    messages: List[MessageRecord] = []
    for index, record in enumerate(raw_messages):
        record_dict = _as_dict(record)
        if record_dict is None:
            continue
        agent_id = _first(record_dict, _AGENT_KEYS)
        round_no = _as_int(_first(record_dict, _ROUND_KEYS))
        if agent_id is None or round_no is None:
            warnings.append(f"messages[{index}] missing agent id or round; skipped")
            continue
        messages.append(
            MessageRecord(
                agent_id=str(agent_id),
                round=round_no,
                content=_first(record_dict, _OPINION_TEXT_KEYS),
                recipient_id=_first(record_dict, _RECIPIENT_KEYS),
                raw=record_dict,
            )
        )

    agent_ids = sorted({o.agent_id for o in opinions} | {m.agent_id for m in messages})
    rounds = sorted({o.round for o in opinions} | {m.round for m in messages})

    if opinions and len(rounds) < 2:
        warnings.append(
            "fewer than 2 rounds: change/agreement/influence will be insufficient_data"
        )
    if opinions and len(agent_ids) < 2:
        warnings.append(
            "fewer than 2 agents: agreement/influence will be insufficient_data"
        )

    summary = DiscussionSummary(
        discussion_id=as_dict.get("discussion_id") or as_dict.get("id"),
        topic=as_dict.get("topic"),
        agent_ids=agent_ids,
        rounds=rounds,
        n_agents=len(agent_ids),
        n_rounds=len(rounds),
        n_opinions=len(opinions),
        n_messages=len(messages),
    )

    normalized = NormalizedHistory(
        raw=history,
        as_dict=as_dict,
        opinions=opinions,
        messages=messages,
        summary=summary,
    )

    if errors:
        if strict:
            raise ValidationError("; ".join(errors))
        return ValidationResult(False, errors, warnings, normalized)

    return ValidationResult(True, errors, warnings, normalized)


def _fail(errors: List[str], strict: bool) -> ValidationResult:
    if strict:
        raise ValidationError("; ".join(errors))
    return ValidationResult(False, errors, [], None)


def is_valid_history(history: Any) -> bool:
    """One-liner for teammates who just want a boolean."""
    return validate_history(history).is_valid