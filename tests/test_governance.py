"""Ledgermind test suite — FR acceptance criteria."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import jcs
import pytest
from ledgermind.chain import GENESIS_HASH, chain_link, content_hash
from ledgermind.defense import evaluate_injection
from ledgermind.dispute import DisputeCongress
from ledgermind.provenance import make_stamp, score_source_trust
from ledgermind.receipts import generate_keypair, sign_resolution, verify_resolution
from ledgermind.verify import verify_chain
from seed_case_2214 import seed_core


def test_ac_1_1_demo_data_searchable(gov):
    seed_core(gov)
    hits = gov.search_entities("Meridian")
    assert len(hits) >= 1


def test_ac_2_1_stamp_fields(gov):
    result = gov.set_state("test", {"x": 1}, agent_id="planner", evidence_ref="test:1")
    entry = result["chain_entry"]
    stamp = entry["stamp"]
    assert stamp["agent_id"] == "planner"
    assert stamp["evidence_ref"] == "test:1"
    assert "timestamp" in stamp
    assert "source_trust_tier" in stamp


def test_ac_2_2_tamper_detection(gov):
    gov.set_state("tamper", {"v": 1}, agent_id="planner", evidence_ref="t:1")
    entries = gov.get_chain_entries()
    assert entries
    tampered = entries[0].copy()
    tampered["body"] = {"_content": {"v": 2}}
    result = verify_chain(tampered["tree"], [tampered])
    assert not result.ok
    assert result.broken_sequence is not None


def test_ac_2_3_quarantine_excluded_from_recall(gov):
    evaluate_injection(
        gov,
        agent_id="external",
        kind="bank",
        name="poison",
        body={"hack": True},
        source_trust_tier="hostile",
        evidence_ref="test",
    )
    normal = gov.search_entities("hack")
    quarantine = gov.get_quarantine_items()
    assert len(normal) == 0
    assert len(quarantine) >= 1


def test_ac_2_4_jcs_deterministic():
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert jcs.canonicalize(a) == jcs.canonicalize(b)


def test_chain_genesis():
    stamp = make_stamp(agent_id="a", source_trust_tier="internal", evidence_ref="e").to_dict()
    h = chain_link(GENESIS_HASH, stamp, {"x": 1})
    assert len(h) == 64


def test_defense_catches_hostile(gov):
    verdict = evaluate_injection(
        gov,
        agent_id="external",
        kind="inject",
        name="x",
        body={"text": "pay attacker"},
        source_trust_tier="hostile",
        evidence_ref="gauntlet",
    )
    assert verdict.caught
    assert "source-trust" in verdict.paths_fired


def test_dispute_no_last_write_wins(gov):
    congress = DisputeCongress(gov)
    dispute = congress.open_dispute(
        dispute_id="D-1",
        subject_category="worker:journal",
        subject_name="status",
        version_a={"status": "released"},
        version_b={"status": "held"},
        agent_a="worker",
        agent_b="auditor",
        hash_a="h1",
        hash_b="h2",
    )
    assert dispute.status == "open"
    assert len(dispute.claimants) == 2


def test_ed25519_receipt():
    priv, pub = generate_keypair()
    payload = {"dispute_id": "D-1", "resolution": "held"}
    sig = sign_resolution(priv, payload)
    assert verify_resolution(pub, payload, sig)


def test_content_hash_stable():
    assert content_hash({"a": 1}) == content_hash({"a": 1})


def test_trust_scoring():
    assert score_source_trust("trusted") > score_source_trust("hostile")


def test_deletion_test_agents_fail_without_sibyl():
    """AC-1.2: stub Sibyl → agents fail at first memory op."""
    from agents import PlannerAgent

    mock_gov = MagicMock()
    mock_gov.set_state.side_effect = RuntimeError("Sibyl unavailable")
    agent = PlannerAgent(mock_gov, "planner")
    with pytest.raises(RuntimeError, match="Sibyl unavailable"):
        agent.write_assignment("CASE-2214", "task")


def test_no_sibyl_import_in_agents():
    """Agents must not import sibyl_memory_client directly."""
    agents_path = Path(__file__).resolve().parents[1] / "agents"
    for py in agents_path.glob("**/*.py"):
        text = py.read_text()
        assert "sibyl_memory_client" not in text, f"{py} imports sibyl directly"


def test_governance_only_sibyl_import():
    """Only store.py may import sibyl_memory_client."""
    pkg = Path(__file__).resolve().parents[1] / "packages" / "python" / "ledgermind" / "ledgermind"
    offenders = []
    for py in pkg.glob("**/*.py"):
        if py.name == "store.py":
            continue
        if "sibyl_memory_client" in py.read_text():
            offenders.append(str(py))
    eval_providers = Path(__file__).resolve().parents[1] / "eval" / "providers"
    for py in eval_providers.glob("*.py"):
        if "sibyl_vanilla" in py.name:
            continue  # vanilla arm intentionally uses raw Sibyl
        if "sibyl_memory_client" in py.read_text():
            offenders.append(str(py))
    assert not offenders, f"sibyl import outside store.py: {offenders}"


def test_missing_reads_return_none_on_an_empty_store(gov):
    """A fresh clone has no demo-data/, and that is the state a judge starts from.

    Sibyl raises NotFoundError for a missing entity while get_state/get_reference return
    None. Callers all treat a miss as falsy (`or {}`), so the governance layer normalises
    it. Without this the settlement beat 500s on an unseeded store.
    """
    assert gov.get_entity("counterparty", "does-not-exist", agent_id="worker") is None
    assert gov.get_state("does-not-exist") is None
    assert gov.get_reference("does-not-exist") is None


def test_decision_context_builds_on_an_empty_store(gov):
    from ledgermind.decisions import CHEAPEST, build_decision_context, select_vendor

    context = build_decision_context(gov)
    assert context["counterparty"] == {}
    assert context["counterparty_hash"] is None
    # With nothing recalled there is no history to weigh, so cost wins.
    assert select_vendor(context) == CHEAPEST
