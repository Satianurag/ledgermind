"""On-Base checkpoint anchoring for chain-head hashes (FR-3 rollback)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ledgermind.chain import content_hash
from web3 import Web3

from onchain.network import DEFAULT_RPC_URL, load_network_env

RECEIPTS_DIR = Path(__file__).resolve().parents[1] / "demo-data" / "onchain"
CHECKPOINT_FILE = RECEIPTS_DIR / "checkpoints.jsonl"


def _rpc_url() -> str:
    load_network_env()
    network = os.environ.get("ONCHAIN_NETWORK", "base-sepolia")
    if "sepolia" in network:
        return os.environ.get("BASE_RPC_URL", DEFAULT_RPC_URL)
    return os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")


def anchor_checkpoint(label: str, chain_head_hash: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Anchor chain-head hash: persist receipt + optional onchain self-transfer tx."""
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "label": label,
        "chain_head_hash": chain_head_hash,
        "content_hash": content_hash({"head": chain_head_hash, "label": label}),
        "anchored_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metadata": metadata or {},
        "tx_hash": None,
        "explorer_url": None,
    }

    # The signer lives in demo-data/onchain/wallet.json; only the CDP bootstrap path
    # exported it to EVM_PRIVATE_KEY, so a plain `make demo` never anchored anything and
    # every checkpoint silently recorded anchor_method=local_receipt while the README
    # claimed rollback restores to an on-Base checkpoint.
    private_key = os.environ.get("EVM_PRIVATE_KEY", "")
    if not private_key:
        try:
            from onchain.cdp_wallet import load_wallet_state

            private_key = (load_wallet_state() or {}).get("private_key", "")
        except Exception:  # noqa: BLE001 - anchoring is best-effort
            private_key = ""

    if private_key:
        try:
            w3 = Web3(Web3.HTTPProvider(_rpc_url()))
            account = w3.eth.account.from_key(private_key)
            nonce = w3.eth.get_transaction_count(account.address)
            tx = {
                "from": account.address,
                "to": account.address,
                "value": 0,
                "nonce": nonce,
                "maxFeePerGas": w3.eth.gas_price,
                "maxPriorityFeePerGas": w3.to_wei(0.001, "gwei"),
                "chainId": w3.eth.chain_id,
                # The chain head rides in the calldata: 64 hex chars at 16 gas per
                # non-zero byte, so the flat 21000 used before was below the intrinsic
                # cost and every anchor would have reverted as "intrinsic gas too low".
                "data": w3.to_hex(text=chain_head_hash[:64]),
            }
            tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.2)
            signed = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            # web3 v7 returns the digest without a 0x prefix. Receipt validation
            # (is_live_tx_hash) requires ^0x[0-9a-f]{64}$, and explorer links need it too,
            # so a bare digest would make a genuine anchor read as a fake one.
            tx_hex = tx_hash.hex()
            if not tx_hex.startswith("0x"):
                tx_hex = "0x" + tx_hex
            base = "sepolia.basescan.org" if "sepolia" in _rpc_url() else "basescan.org"
            record["tx_hash"] = tx_hex
            record["explorer_url"] = f"https://{base}/tx/{tx_hex}"
            record["anchor_method"] = "self_transfer_memo"
        except Exception as exc:
            record["anchor_error"] = str(exc)[:300]
            record["anchor_method"] = "local_only"
    else:
        record["anchor_method"] = "local_receipt"

    with CHECKPOINT_FILE.open("a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def load_latest_checkpoint(label: str | None = None) -> dict[str, Any] | None:
    if not CHECKPOINT_FILE.exists():
        return None
    lines = CHECKPOINT_FILE.read_text().strip().splitlines()
    if not lines:
        return None
    if label:
        for line in reversed(lines):
            rec = json.loads(line)
            if rec.get("label") == label:
                return rec
        return None
    return json.loads(lines[-1])
