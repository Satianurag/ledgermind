"""Beat data, independent of how it is rendered.

Each function returns plain JSON-serialisable data. `ui/app.py` renders it through Jinja
for the fallback UI and serves it verbatim under /api/* for the Next.js front end, so the
two surfaces can never disagree about what happened.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from typing import Any

from ledgermind.decisions import build_decision_context, explain_flip, select_vendor
from ledgermind.defense import evaluate_injection
from ledgermind.diff import diff_snapshots, render_rich_table, snapshot_entities
from ledgermind.dispute import DisputeCongress
from ledgermind.rollback import RollbackManager
from ledgermind.store import GovernedMemoryClient
from ledgermind.telemetry import TelemetryLogger

from onchain import write_receipts_to_governance
from ui.poison_cards import POISON_CARDS

HEIST_CHECKPOINT = "pre-heist"


def commit_hash() -> str:
    """The rules require an on-screen commit hash in the fresh-session segment."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:  # noqa: BLE001
        return "dev"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _provenance(record: dict[str, Any]) -> dict[str, Any]:
    return record.get("stamp", {}) if isinstance(record, dict) else {}


def state_data(gov: GovernedMemoryClient) -> dict[str, Any]:
    """Chain, tiers and verification status — the 'memory is load-bearing' surface."""
    entries = gov.get_chain_entries()
    verifications = gov.verify_all()
    entities = gov.raw.list_entities()

    tiers: dict[str, int] = {}
    for entry in entries:
        tier = str(entry.get("tree", "")).split(":", 1)[0] or "unknown"
        tiers[tier] = tiers.get(tier, 0) + 1

    chain = [
        {
            "tree": e.get("tree"),
            "sequence": e.get("sequence"),
            "prev_hash": e.get("prev_hash"),
            "hash": e.get("hash"),
            "agent_id": _provenance(e).get("agent_id"),
            "timestamp": _provenance(e).get("timestamp"),
            "source_trust_tier": _provenance(e).get("source_trust_tier"),
            "evidence_ref": _provenance(e).get("evidence_ref"),
        }
        for e in sorted(entries, key=lambda x: (x.get("tree", ""), x.get("sequence", 0)))
    ]

    return {
        "commit": commit_hash(),
        "timestamp": utc_now(),
        "chain": chain,
        "chain_length": len(chain),
        "tiers": tiers,
        "entity_count": len(entities),
        "quarantined": len(gov.get_quarantine_items()),
        "verification": {
            "trees": len(verifications),
            "all_ok": all(v.get("ok") for v in verifications) if verifications else True,
            "broken": [v for v in verifications if not v.get("ok")],
        },
        "poison_cards": POISON_CARDS,
    }


def inject_data(gov: GovernedMemoryClient, card_id: str, text: str = "") -> dict[str, Any]:
    card = next((c for c in POISON_CARDS if c["id"] == card_id), POISON_CARDS[0])
    RollbackManager(gov).capture(HEIST_CHECKPOINT)
    verdict = evaluate_injection(
        gov,
        agent_id="external",
        kind="counterparty",
        name="meridian-bank-update",
        body={"instruction": text or card["text"]},
        source_trust_tier=card["tier"],
        evidence_ref=f"judge:{card_id}",
        simulate_chain_break=card.get("simulate_chain_break", False),
    )
    return {"card": card, "verdict": verdict.to_dict(), "timestamp": utc_now()}


def rollback_data(gov: GovernedMemoryClient) -> dict[str, Any]:
    return {"result": RollbackManager(gov).restore(HEIST_CHECKPOINT), "timestamp": utc_now()}


def congress_data(gov: GovernedMemoryClient) -> dict[str, Any]:
    """Two agents disagree; the dispute keeps both versions and resolves with a receipt."""
    congress = DisputeCongress(gov)
    worker = gov.set_entity(
        "journal", "payout-status", {"status": "released"},
        agent_id="worker", evidence_ref="congress:vesper",
    )
    auditor = gov.set_entity(
        "journal", "payout-status-held", {"status": "held"},
        agent_id="auditor", evidence_ref="congress:kestrel",
    )
    tree = auditor.get("chain_entry", {}).get("tree", "") or worker.get("chain_entry", {}).get("tree", "")

    dispute = congress.open_dispute(
        dispute_id="CASE-2214-01",
        subject_category="worker:journal",
        subject_name="payout-status",
        version_a={"status": "released"},
        version_b={"status": "held"},
        agent_a="worker",
        agent_b="auditor",
        hash_a=worker.get("content_hash", ""),
        hash_b=auditor.get("content_hash", ""),
    )
    citations = [{"tree": tree}] if tree else []
    dispute, arbiter = congress.arbitrate_with_vertex(
        dispute, citations=citations, fallback_winner_idx=1, confidence=0.92
    )
    dispute = congress.await_human_gate(dispute, approved=True)
    congress.promote_resolution(dispute, subject_kind="journal", agent_id="worker")
    return {"dispute": dispute.to_body(), "arbiter": arbiter, "timestamp": utc_now()}


def settlement_data(gov: GovernedMemoryClient) -> dict[str, Any]:
    data = write_receipts_to_governance(gov)
    context = build_decision_context(gov)
    decision = select_vendor(context)
    telemetry = TelemetryLogger(gov)
    counterparty = context.get("counterparty") or {}
    entry = telemetry.log_decision(
        agent="governance",
        citations=[telemetry.build_citation("counterparty:meridian", counterparty)],
        outcome=decision,
        ts=utc_now(),
    )
    telemetry.save_manifest(run_id=commit_hash(), versions={"ledgermind": "0.1.0"})
    flip = telemetry.counterfactual_replay(select_vendor, context, remove_key="counterparty")
    return {
        **data,
        "decision": decision,
        "why": explain_flip(context, decision),
        "counterparty": counterparty,
        "counterparty_hash": context.get("counterparty_hash"),
        "flip": flip,
        "entry": entry.to_dict(),
        "timestamp": utc_now(),
    }


def montage_data(gov: GovernedMemoryClient) -> dict[str, Any]:
    before = snapshot_entities(gov.raw.list_entities())
    gov.set_entity(
        "case", "CASE-2214",
        {"status": "resolved", "invoice": "INV-8841"},
        agent_id="planner", evidence_ref="montage:tier-promotion",
    )
    after = snapshot_entities(gov.raw.list_entities())
    diff = diff_snapshots(before, after)
    return {"diff": diff, "table": render_rich_table(diff), "timestamp": utc_now()}


def diff_data(gov: GovernedMemoryClient) -> dict[str, Any]:
    snapshot = snapshot_entities(gov.raw.list_entities())
    return {
        "diff": {"snapshot": snapshot},
        "table": f"{len(snapshot)} entities indexed",
        "timestamp": utc_now(),
    }


def recall_data(gov: GovernedMemoryClient) -> dict[str, Any]:
    """Fresh-session beat: what a cold start recalls, and what it decides because of it."""
    context = build_decision_context(gov)
    decision = select_vendor(context)
    flip = TelemetryLogger(gov).counterfactual_replay(
        select_vendor, context, remove_key="counterparty"
    )
    return {
        "commit": commit_hash(),
        "timestamp": utc_now(),
        "priority": context.get("priority"),
        "counterparty": context.get("counterparty"),
        "counterparty_hash": context.get("counterparty_hash"),
        "policy": context.get("policy"),
        "events": len(context.get("receipts") or []),
        "decision": decision,
        "why": explain_flip(context, decision),
        "counterfactual": flip,
    }
