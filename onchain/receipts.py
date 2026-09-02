"""Live onchain receipt validation — no test fixtures in demo paths."""

from __future__ import annotations

import re
from typing import Any

TX_HASH_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")
FAKE_TX_PATTERNS = (
    re.compile(r"^0x(a{8,}|b{8,}|c{8,}|d{8,}|e{8,}|f{8,})"),
)


def is_live_tx_hash(tx_hash: str | None) -> bool:
    if not tx_hash or not TX_HASH_RE.match(tx_hash):
        return False
    return not any(p.match(tx_hash) for p in FAKE_TX_PATTERNS)


def is_live_receipt(receipt: dict[str, Any] | None, *, require_tx: bool = True) -> bool:
    if not receipt:
        return False
    if receipt.get("source") not in ("live", "persisted"):
        return False
    if require_tx and receipt.get("kind") in ("x402", "acp", "checkpoint"):
        return is_live_tx_hash(str(receipt.get("tx_hash", "")))
    if receipt.get("kind") == "b20":
        return receipt.get("source") in ("live", "persisted") and receipt.get("activated") is not None
    return True


def require_live_receipt(receipt: dict[str, Any] | None, *, kind: str) -> dict[str, Any]:
    if not is_live_receipt(receipt, require_tx=kind != "b20"):
        raise RuntimeError(
            f"Missing or invalid live {kind} receipt. "
            f"Run: make bootstrap-onchain (requires CDP keys + ACP agent)."
        )
    return receipt
