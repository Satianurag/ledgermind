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

    private_key = os.environ.get("EVM_PRIVATE_KEY", "")
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
                "gas": 21000,
                "maxFeePerGas": w3.eth.gas_price,
                "maxPriorityFeePerGas": w3.to_wei(0.001, "gwei"),
                "chainId": w3.eth.chain_id,
                "data": w3.to_hex(text=chain_head_hash[:64]),
            }
            signed = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hex = tx_hash.hex()
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
