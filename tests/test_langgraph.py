"""LangGraph reference deployment wiring — decisions must come from memory."""

from __future__ import annotations

import tempfile
from pathlib import Path

from ledgermind.store import GovernedMemoryClient

from agents.graph import build_demo_graph


def _seeded(
    gov: GovernedMemoryClient, amount_usd: int, *, preapproved: bool = False
) -> None:
    gov.set_entity(
        "case",
        "CASE-2214",
        {
            "invoice": "INV-8841",
            "amount_usd": amount_usd,
            "counterparty": "Meridian Components Ltd",
            "status": "payout_exception",
            "preapproved": preapproved,
        },
        agent_id="planner",
        evidence_ref="test:case",
    )
    gov.set_reference(
        "policy:vendor-payout",
        {"dual_approval_threshold_usd": 10000},
        agent_id="auditor",
        evidence_ref="test:policy",
    )


def test_demo_graph_runs_four_nodes():
    tmp = tempfile.mkdtemp()
    with GovernedMemoryClient(Path(tmp) / "graph.db") as gov:
        _seeded(gov, 12400)
        result = build_demo_graph(gov).invoke({"case_id": "CASE-2214", "messages": []})
    assert result["outcome"] == "audited"
    assert len(result["messages"]) == 4
    assert result["recalled_from_memory"] is True


def test_payout_decision_is_read_from_memory_not_hardcoded():
    """Same graph, different remembered amount, different decision."""
    over = tempfile.mkdtemp()
    with GovernedMemoryClient(Path(over) / "over.db") as gov:
        _seeded(gov, 12400)  # above the remembered $10,000 threshold
        high = build_demo_graph(gov).invoke({"case_id": "CASE-2214", "messages": []})

    under = tempfile.mkdtemp()
    with GovernedMemoryClient(Path(under) / "under.db") as gov:
        _seeded(gov, 400)  # below it
        low = build_demo_graph(gov).invoke({"case_id": "CASE-2214", "messages": []})

    assert high["audit"]["requires_dual_approval"] is True
    assert low["audit"]["requires_dual_approval"] is False
    assert "held" in high["messages"][1]
    assert "released" in low["messages"][1]


def test_contradiction_is_detected_not_scripted():
    """A dispute opens only when two remembered records actually disagree."""
    tmp = tempfile.mkdtemp()
    with GovernedMemoryClient(Path(tmp) / "agree.db") as gov:
        _seeded(gov, 400)  # worker and auditor both conclude "released"
        agreed = build_demo_graph(gov).invoke({"case_id": "CASE-2214", "messages": []})
    assert agreed["contradiction"] is False
    assert agreed["dispute"] is None

    # A pre-approval on the case makes the worker release an amount the auditor holds.
    tmp2 = tempfile.mkdtemp()
    with GovernedMemoryClient(Path(tmp2) / "conflict.db") as gov:
        _seeded(gov, 12400, preapproved=True)
        conflict = build_demo_graph(gov).invoke({"case_id": "CASE-2214", "messages": []})
    assert conflict["contradiction"] is True
    assert conflict["dispute"] is not None
    claimants = conflict["dispute"]["claimants"]
    assert {c["agent_id"] for c in claimants} == {"worker", "auditor"}
    assert claimants[0]["content"]["status"] != claimants[1]["content"]["status"]
