"""x402 buyer client — live WeatherXM testnet payment (FR-6)."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

RECEIPTS_DIR = Path(__file__).resolve().parents[1] / "demo-data" / "onchain"
X402_RECEIPT_FILE = RECEIPTS_DIR / "x402_receipt.json"

# Live x402 seller on Base Sepolia (WeatherXM Agent API testnet)
DEFAULT_X402_URL = os.environ.get(
    "X402_TEST_URL",
    "https://agent-testnet.weatherxm.com/api/current?lat=37.98&lon=23.73&units=metric",
)


def _explorer_tx(tx_hash: str) -> str:
    network = os.environ.get("ONCHAIN_NETWORK", "base-sepolia")
    base = "https://sepolia.basescan.org" if "sepolia" in network else "https://basescan.org"
    return f"{base}/tx/{tx_hash}"


def _persist_receipt(receipt: dict[str, Any]) -> None:
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    X402_RECEIPT_FILE.write_text(json.dumps(receipt, indent=2))


def load_persisted_receipt() -> dict[str, Any] | None:
    from onchain.receipts import is_live_receipt

    if X402_RECEIPT_FILE.exists():
        receipt = json.loads(X402_RECEIPT_FILE.read_text())
        if is_live_receipt(receipt):
            return receipt
    return None


def _extract_tx_hash(settle: Any) -> str:
    if settle is None:
        return ""
    if hasattr(settle, "model_dump"):
        settle = settle.model_dump()
    if not isinstance(settle, dict):
        return ""
    for key in ("transaction", "txHash", "transaction_hash", "tx_hash"):
        val = settle.get(key)
        if val:
            return str(val)
    success = settle.get("success") or {}
    if isinstance(success, dict):
        for key in ("transaction", "txHash", "transaction_hash"):
            val = success.get(key)
            if val:
                return str(val)
    return ""


async def _execute_x402_payment(url: str, signer: Any) -> dict[str, Any]:
    from x402 import x402Client
    from x402.http import x402HTTPClient
    from x402.http.clients import x402HttpxClient
    from x402.mechanisms.evm import EthAccountSigner
    from x402.mechanisms.evm.exact.register import register_exact_evm_client

    client = x402Client()
    wrapped = signer if hasattr(signer, "sign_typed_data") else EthAccountSigner(signer)
    register_exact_evm_client(client, wrapped)
    http_client = x402HTTPClient(client)

    async with x402HttpxClient(client) as http:
        response = await http.get(url)
        await response.aread()
        settle = None
        if response.is_success:
            settle = http_client.get_payment_settle_response(lambda name: response.headers.get(name))
        payer = getattr(signer, "address", None) or str(signer)
        return {
            "ok": response.is_success,
            "status": response.status_code,
            "body_preview": (response.text or "")[:500],
            "settle": settle.model_dump() if settle and hasattr(settle, "model_dump") else settle,
            "payer": payer,
        }


def execute_x402(url: str | None = None, *, force: bool = False) -> dict[str, Any]:
    """Run live x402 payment; persist receipt with onchain tx hash."""
    load_dotenv()
    os.environ.setdefault("ONCHAIN_NETWORK", "base-sepolia")

    if not force:
        persisted = load_persisted_receipt()
        if persisted:
            persisted["source"] = "persisted"
            return persisted

    from onchain.cdp_wallet import bootstrap_cdp_wallet, get_evm_signer, usdc_balance

    bootstrap = bootstrap_cdp_wallet()
    if not bootstrap.get("ok"):
        raise RuntimeError(bootstrap.get("error", "wallet bootstrap failed"))

    signer = get_evm_signer()
    payer = getattr(signer, "address", str(signer))
    balance = usdc_balance(payer)
    if balance < 1000:  # 0.001 USDC
        raise RuntimeError(
            f"Insufficient USDC on {payer} ({balance} raw). "
            "Fund via CDP faucet or Circle faucet (Base Sepolia)."
        )

    target = url or DEFAULT_X402_URL
    result = asyncio.run(_execute_x402_payment(target, signer))
    tx_hash = _extract_tx_hash(result.get("settle"))
    if not tx_hash:
        raise RuntimeError(f"x402 payment did not settle: status={result.get('status')} result={result}")

    receipt = {
        "kind": "x402",
        "tx_hash": tx_hash,
        "explorer_url": _explorer_tx(tx_hash),
        "x402scan_url": f"https://x402scan.com/tx/{tx_hash}",
        "amount_usdc": 0.001,
        "network": os.environ.get("ONCHAIN_NETWORK", "base-sepolia"),
        "url": target,
        "executed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "live",
        "payer": payer,
        "result": result,
    }
    _persist_receipt(receipt)
    return receipt


def execute_or_load_x402(url: str | None = None) -> dict[str, Any]:
    """Return a validated live x402 receipt (execute or load from disk)."""
    persisted = load_persisted_receipt()
    if persisted:
        return persisted
    return execute_x402(url, force=True)
