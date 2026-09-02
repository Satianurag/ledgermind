"""Commercial vendor decision — cheapest vs reliable (fresh-session flip).

The decision must turn on *remembered counterparty history*. An earlier version also
flipped on `receipts` being non-empty, which is true after any seed, so the outcome was
over-determined: it looked memory-driven while actually being constant. Counterfactual
replay only means something if removing the citation can change the answer.
"""

from __future__ import annotations

from typing import Any

from ledgermind.chain import content_hash
from ledgermind.store import GovernedMemoryClient

RELIABLE = "reliable-vendor (DataTrust Analytics)"
CHEAPEST = "cheapest-vendor (BudgetData Co)"

DEFAULT_RELIABILITY_THRESHOLD = 0.75
DEFAULT_INCIDENT_THRESHOLD = 3


def select_vendor(context: dict[str, Any]) -> str:
    """Reliability outweighs unit cost — but only when history is actually remembered."""
    counterparty = context.get("counterparty") or {}
    if not counterparty:
        # No recalled history: the policy has nothing to weigh, so cost wins by default.
        return CHEAPEST

    policy = context.get("policy") or {}
    reliability_floor = policy.get("reliability_threshold", DEFAULT_RELIABILITY_THRESHOLD)
    incident_floor = policy.get("incident_threshold", DEFAULT_INCIDENT_THRESHOLD)

    reliability = counterparty.get("reliability_score")
    incidents = counterparty.get("late_deliveries", 0) + counterparty.get("overcharges", 0)

    if reliability is not None and reliability < reliability_floor:
        return RELIABLE
    if incidents >= incident_floor:
        return RELIABLE
    return CHEAPEST


def build_decision_context(gov: GovernedMemoryClient) -> dict[str, Any]:
    """Recall counterparty history + policy + receipts for the fresh-session decision."""
    counterparty = gov.get_entity("counterparty", "meridian-components-ltd", agent_id="worker") or {}
    dispute_receipt = gov.get_reference("receipt:CASE-2214-01") or {}
    return {
        "counterparty": counterparty,
        # The hash is what the telemetry panel cites on screen, so it has to be the real
        # content hash of the recalled item, not a placeholder string.
        "counterparty_hash": content_hash(counterparty) if counterparty else None,
        "policy": gov.get_reference("policy:vendor-payout") or {},
        "resolved_disputes": 1 if dispute_receipt else 0,
        "receipts": gov.read_events(limit=20),
        "priority": gov.get_state("priorities"),
    }


def explain_flip(context: dict[str, Any], outcome: str) -> str:
    counterparty = context.get("counterparty") or {}
    cp_hash = context.get("counterparty_hash") or "unrecalled"
    if outcome == RELIABLE:
        reliability = counterparty.get("reliability_score")
        incidents = counterparty.get("late_deliveries", 0) + counterparty.get("overcharges", 0)
        return (
            f"Flipped to the reliable vendor because recalled memory item {cp_hash[:16]} "
            f"records reliability {reliability} across {incidents} prior incidents."
        )
    return (
        "Default cheapest-vendor policy applied — no counterparty history was recalled, "
        "so there was nothing to weigh against unit cost."
    )
