"""Onchain settlement sidecar — receipts return to governance, never direct Sibyl writes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ledgermind.config import get_settings

from onchain.acp import load_persisted_receipt as load_acp_receipt
from onchain.b20 import read_b20
from onchain.receipts import is_live_receipt
from onchain.receipts import require_live_receipt as require_live_receipt  # re-export for bootstrap
from onchain.wallet import enforce_cap
from onchain.x402 import load_persisted_receipt as load_x402_receipt

RECEIPTS_DIR = Path(__file__).resolve().parents[1] / "demo-data" / "onchain"


def load_settlement_receipts() -> dict[str, Any]:
    """Load whatever live onchain receipts this checkout has.

    Never raises and never synthesises. demo-data/ is gitignored, so a fresh clone -- which
    is exactly what a judge does -- has no receipts at all. The settlement beat must still
    render, reporting honestly which stacks were exercised and which were not, rather than
    500ing. Use require_live_receipt() on the bootstrap path, where a missing or fake
    receipt genuinely should be a hard failure.
    """
    receipts: list[dict[str, Any]] = []
    unexercised: list[str] = []

    x402 = load_x402_receipt()
    if is_live_receipt(x402, require_tx=True):
        receipts.append(x402)
    else:
        unexercised.append("x402")

    b20_file = RECEIPTS_DIR / "b20_receipt.json"
    b20 = None
    if b20_file.exists():
        try:
            b20 = json.loads(b20_file.read_text())
        except json.JSONDecodeError:
            b20 = None
    if not is_live_receipt(b20, require_tx=False):
        try:
            b20 = read_b20()
            RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
            b20_file.write_text(json.dumps(b20, indent=2))
        except Exception:  # noqa: BLE001 - offline clone must still render the beat
            b20 = None
    if is_live_receipt(b20, require_tx=False):
        receipts.append(b20)
    else:
        unexercised.append("b20")

    acp = load_acp_receipt()
    if is_live_receipt(acp, require_tx=True):
        receipts.append(acp)
    else:
        unexercised.append("acp")

    return {
        "receipts": receipts,
        "unexercised_stacks": unexercised,
        "bootstrap_hint": (
            "No live receipts in this checkout (demo-data/ is gitignored). "
            "Run `make bootstrap-onchain` with CDP keys to execute them."
            if not receipts
            else None
        ),
    }


def collect_settlement_receipts(gov: Any | None = None) -> dict[str, Any]:
    """Live settlement collection (x402 + B20 + ACP) with cap checks."""
    from onchain.acp import execute_or_load_acp_job
    from onchain.x402 import execute_or_load_x402

    settings = get_settings()
    cap_check = (
        enforce_cap(2.50, gov)
        if gov is not None
        else {"allowed": False, "reason": "no governance client", "policy_key": "policy:wallet-cap"}
    )
    over_cap = enforce_cap(0.50, gov) if gov is not None else {"allowed": True}
    x402 = execute_or_load_x402()
    b20 = read_b20()
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    (RECEIPTS_DIR / "b20_receipt.json").write_text(json.dumps(b20, indent=2))
    acp = execute_or_load_acp_job()
    return {
        "cap_check_over": cap_check,
        "cap_check_under": over_cap,
        "receipts": [x402, b20, acp],
        "wallet_cap_usdc": settings.wallet_cap_usdc,
    }


def write_receipts_to_governance(gov: Any) -> dict[str, Any]:
    """Stamp settlement receipts into governed memory."""
    data = load_settlement_receipts()
    cap_over = enforce_cap(2.50, gov)
    cap_under = enforce_cap(0.50, gov)
    data["cap_check_over"] = cap_over
    data["cap_check_under"] = cap_under
    for receipt in data["receipts"]:
        kind = receipt.get("kind", "onchain")
        gov.write_event(
            agent_id="onchain",
            acted={"settlement": kind},
            extra=receipt,
            evidence_ref=f"onchain:{kind}",
        )
        key = f"receipt:{kind}"
        gov.set_reference(key, receipt, agent_id="onchain", evidence_ref=key)
    return data
