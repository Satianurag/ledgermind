"""Vertex arbiter integration for dispute congress (FR-4)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from ledgermind.dispute import DisputeCongress
from ledgermind.store import GovernedMemoryClient


def _gov():
    tmp = tempfile.mkdtemp()
    return GovernedMemoryClient(Path(tmp) / "arbiter.db")


def test_arbitrate_with_vertex_parses_json():
    gov = _gov()
    congress = DisputeCongress(gov)
    w = gov.set_entity(
        "journal",
        "payout-status",
        {"status": "released"},
        agent_id="worker",
        evidence_ref="test:worker",
    )
    a = gov.set_entity(
        "journal",
        "payout-held",
        {"status": "held"},
        agent_id="auditor",
        evidence_ref="test:auditor",
    )
    dispute = congress.open_dispute(
        dispute_id="D-arb",
        subject_category="worker:journal",
        subject_name="payout-status",
        version_a={"status": "released"},
        version_b={"status": "held"},
        agent_a="worker",
        agent_b="auditor",
        hash_a=w["content_hash"],
        hash_b=a["content_hash"],
    )
    tree = a.get("chain_entry", {}).get("tree", "")
    citations = [{"tree": tree}] if tree else []

    vertex_reply = '{"winner_agent": "auditor", "confidence": 0.93, "reasoning": "held matches policy"}'
    with patch("ledgermind.vertex.generate_content", return_value=vertex_reply):
        with patch("ledgermind.dispute.get_settings") as mock_settings:
            mock_settings.return_value.google_cloud_project = "test-project"
            mock_settings.return_value.model_arbiter = "gemini-3.1-pro-preview"
            dispute, meta = congress.arbitrate_with_vertex(dispute, citations=citations, fallback_winner_idx=0)

    assert meta["backend"] == "vertex"
    assert dispute.resolution["winner_agent"] == "auditor"
    assert dispute.confidence == 0.93


def test_arbitrate_falls_back_without_vertex():
    gov = _gov()
    congress = DisputeCongress(gov)
    dispute = congress.open_dispute(
        dispute_id="D-fb",
        subject_category="worker:journal",
        subject_name="status",
        version_a={"status": "released"},
        version_b={"status": "held"},
        agent_a="worker",
        agent_b="auditor",
        hash_a="h1",
        hash_b="h2",
    )
    with patch("ledgermind.dispute.get_settings") as mock_settings:
        mock_settings.return_value.google_cloud_project = ""
        mock_settings.return_value.model_arbiter = "gemini-3.1-pro-preview"
        dispute, meta = congress.arbitrate_with_vertex(
            dispute,
            citations=[{"tree": "warm:worker:journal/status"}],
            fallback_winner_idx=1,
        )
    assert meta["backend"] == "rule-based"
    assert dispute.resolution["winner_agent"] == "auditor"
