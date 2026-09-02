"""The JS verifier must agree with the Python chain byte-for-byte.

The npm package is an independent reimplementation so that a third party can check a
receipt chain without trusting this codebase. That guarantee is only real if the two
implementations cannot drift, so CI runs the JS verifier against a chain Python produced.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from ledgermind.store import GovernedMemoryClient

ROOT = Path(__file__).resolve().parents[1]
NPM_CLI = ROOT / "packages" / "npm" / "ledgermind" / "bin" / "ledgermind.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def _export(gov: GovernedMemoryClient) -> dict:
    return {"format": "ledgermind-chain-v1", "entries": gov.get_chain_entries()}


def _run(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", str(NPM_CLI), "verify", str(path)],
        capture_output=True, text=True, cwd=str(ROOT),
    )


@pytest.fixture
def chain_file(gov, tmp_path):
    gov.set_entity("case", "CASE-2214", {"amount_usd": 12400, "note": "ünïcødé ✓"},
                   agent_id="planner", evidence_ref="test:a")
    gov.set_entity("case", "CASE-2214", {"amount_usd": 12500, "note": "revised"},
                   agent_id="planner", evidence_ref="test:b")
    gov.set_reference("policy:vendor-payout", {"dual_approval_threshold_usd": 10000},
                      agent_id="auditor", evidence_ref="test:policy")
    path = tmp_path / "chain.json"
    path.write_text(json.dumps(_export(gov), indent=2))
    return path


def test_js_verifier_accepts_a_python_written_chain(chain_file):
    result = _run(chain_file)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 broken" in result.stdout


def test_js_verifier_rejects_a_tampered_body(chain_file, tmp_path):
    payload = json.loads(chain_file.read_text())
    target = next(
        e for e in payload["entries"] if e["body"].get("_content", {}).get("amount_usd") == 12400
    )
    target["body"]["_content"]["amount_usd"] = 12401  # one digit
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload, indent=2))

    result = _run(tampered)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "BROKEN" in result.stdout
    assert f"sequence {target['sequence']}" in result.stdout


def test_js_package_self_test_passes():
    result = subprocess.run(
        ["node", "test.js"], capture_output=True, text=True,
        cwd=str(ROOT / "packages" / "npm" / "ledgermind"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
