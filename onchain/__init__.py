"""Onchain settlement sidecar — receipts return to governance, never direct Sibyl writes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ledgermind.config import get_settings

from onchain.acp import load_persisted_receipt as load_acp_receipt
from onchain.b20 import read_b20
from onchain.receipts import is_live_receipt, require_live_receipt
from onchain.wallet import enforce_cap
from onchain.x402 import load_persisted_receipt as load_x402_receipt

RECEIPTS_DIR = Path(__file__).resolve().parents[1] / "demo-data" / "onchain"


def load_settlement_receipts() -> dict[str, Any]:
    """Load verified live onchain receipts from disk."""
    x402 = load_x402_receipt()
    acp = load_acp_receipt()
    b20_file = RECEIPTS_DIR / "b20_receipt.json"
    if b20_file.exists():
        b20 = json.loads(b20_file.read_text())
        if not is_live_receipt(b20, require_tx=False):
            b20 = read_b20()
            RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
            b20_file.write_text(json.dumps(b20, indent=2))
    else:
        b20 = read_b20()
        RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
        b20_file.write_text(json.dumps(b20, indent=2))
    require_live_receipt(x402, kind="x402")
    require_live_receipt(b20, kind="b20")
    receipts = [x402, b20]
    unexercised: list[str] = []
    # ACP is optional: an unexercised partner stack must be reported as absent,
    # never synthesised, and must not take down the Base settlement beat.
    if is_live_receipt(acp, require_tx=True):
        receipts.append(acp)
    else:
        unexercised.append("acp")
    return {"receipts": receipts, "unexercised_stacks": unexercised}


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
