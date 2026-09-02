"""Commercial vendor decision — cheapest vs reliable (fresh-session flip)."""

from __future__ import annotations

from typing import Any

from ledgermind.store import GovernedMemoryClient


def select_vendor(context: dict[str, Any]) -> str:
    """Decision function: reliability outweighs unit cost when history is remembered."""
    counterparty = context.get("counterparty", {})
    late_deliveries = counterparty.get("late_deliveries", 0)
    resolved_disputes = context.get("resolved_disputes", 0)
    receipts = context.get("receipts", [])

    if late_deliveries >= 3 or resolved_disputes > 0 or receipts:
        return "reliable-vendor (DataTrust Analytics)"
    return "cheapest-vendor (BudgetData Co)"


def build_decision_context(gov: GovernedMemoryClient) -> dict[str, Any]:
    """Recall counterparty history + receipts from Sibyl for fresh-session decision."""
    counterparty = gov.get_entity("counterparty", "meridian-components-ltd", agent_id="worker") or {}
    receipts = gov.read_events(limit=20)
    dispute_receipt = gov.get_reference("receipt:CASE-2214-01") or {}
    return {
        "counterparty": counterparty,
        "resolved_disputes": 1 if dispute_receipt else 0,
        "receipts": receipts,
        "priority": gov.get_state("priorities"),
    }


def explain_flip(context: dict[str, Any], outcome: str) -> str:
    cp_hash = context.get("counterparty", {}).get("_hash", "counterparty:meridian")
    if "reliable" in outcome:
        return f"This decision flipped because memory item {cp_hash} (counterparty history) changed the risk calculus"
    return "Default cheapest-vendor policy applied — no load-bearing memory citations"
