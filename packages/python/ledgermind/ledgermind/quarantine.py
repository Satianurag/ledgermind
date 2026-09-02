"""Quarantine tier semantics — WARM quarantine:* excluded from normal recall."""

from __future__ import annotations

QUARANTINE_PREFIX = "quarantine:"


def is_quarantine_category(category: str) -> bool:
    return category.startswith(QUARANTINE_PREFIX)


def quarantine_category(agent_id: str) -> str:
    return f"{QUARANTINE_PREFIX}{agent_id}"


def should_exclude_from_recall(category: str) -> bool:
    return is_quarantine_category(category)
