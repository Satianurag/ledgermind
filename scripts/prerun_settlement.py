"""Pre-run settlement: CDP wallet bootstrap + live x402 + B20 + ACP."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from dotenv import load_dotenv

    from onchain.network import load_network_env

    load_dotenv(ROOT / ".env")
    load_network_env()
    from onchain.acp import execute_or_load_acp_job
    from onchain.b20 import read_b20
    from onchain.cdp_wallet import bootstrap_cdp_wallet
    from onchain.checkpoint import anchor_checkpoint
    from onchain.x402 import execute_or_load_x402

    out_dir = ROOT / "demo-data" / "onchain"
    out_dir.mkdir(parents=True, exist_ok=True)

    report: dict = {"steps": []}

    wallet = bootstrap_cdp_wallet()
    report["steps"].append({"wallet": wallet})
    print("Wallet:", wallet.get("source"), wallet.get("address", wallet.get("error", "")))

    # B20 — live mainnet read-only (free; tokenized stocks not on Sepolia)
    b20 = read_b20()
    (out_dir / "b20_receipt.json").write_text(json.dumps(b20, indent=2))
    report["steps"].append({"b20": b20})
    print("B20 read OK:", b20.get("explorer_url"))

    x402 = execute_or_load_x402()
    report["steps"].append({"x402": x402})
    print("x402:", x402.get("source"), x402.get("explorer_url"))

    acp = execute_or_load_acp_job()
    report["steps"].append({"acp": acp})
    print("ACP:", acp.get("source"), acp.get("explorer_url"))

    checkpoint = anchor_checkpoint(
        "settlement-prerun", b20.get("multiplier", ""), {"x402": x402.get("tx_hash")}
    )
    checkpoint_receipt = {**checkpoint, "kind": "checkpoint", "source": "live"}
    (out_dir / "checkpoint_receipt.json").write_text(json.dumps(checkpoint_receipt, indent=2))
    report["steps"].append({"checkpoint": checkpoint})
    print("Checkpoint:", checkpoint.get("explorer_url") or checkpoint.get("anchor_method"))

    (out_dir / "prerun_report.json").write_text(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
