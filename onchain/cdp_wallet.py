"""CDP Agentic Wallet bootstrap: account, faucet, signing (FR-6)."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

WALLET_DIR = Path(__file__).resolve().parents[1] / "demo-data" / "onchain"
WALLET_STATE_FILE = WALLET_DIR / "wallet.json"
CDP_ACCOUNT_NAME = "ledgermind-demo"


def _has_cdp_credentials() -> bool:
    load_dotenv()
    return bool(os.environ.get("CDP_API_KEY_ID") and os.environ.get("CDP_API_KEY_SECRET"))


def _has_wallet_secret() -> bool:
    load_dotenv()
    return bool(os.environ.get("CDP_WALLET_SECRET"))


def load_wallet_state() -> dict[str, Any] | None:
    if WALLET_STATE_FILE.exists():
        return json.loads(WALLET_STATE_FILE.read_text())
    return None


def save_wallet_state(state: dict[str, Any]) -> None:
    WALLET_DIR.mkdir(parents=True, exist_ok=True)
    WALLET_STATE_FILE.write_text(json.dumps(state, indent=2))


async def _bootstrap_cdp_async() -> dict[str, Any]:
    from cdp import CdpClient
    from cdp.evm_local_account import EvmLocalAccount

    existing = load_wallet_state()
    if existing and existing.get("private_key") and existing.get("address"):
        os.environ["EVM_PRIVATE_KEY"] = existing["private_key"]
        os.environ.setdefault("ONCHAIN_NETWORK", existing.get("network", "base-sepolia"))
        return {"ok": True, "source": "persisted_wallet", **existing}

    async with CdpClient() as cdp:
        account = await cdp.evm.get_or_create_account(name=CDP_ACCOUNT_NAME)
        private_key = await cdp.evm.export_account(name=CDP_ACCOUNT_NAME)
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key

        usdc_tx = ""
        eth_tx = ""
        balance = usdc_balance(account.address)
        if balance < 1000:
            try:
                usdc_tx = await cdp.evm.request_faucet(
                    address=account.address,
                    network="base-sepolia",
                    token="usdc",
                )
            except Exception as exc:
                if balance < 1000:
                    raise RuntimeError(f"CDP USDC faucet failed and balance is low: {exc}") from exc
        if usdc_balance(account.address) == 0:
            try:
                eth_tx = await cdp.evm.request_faucet(
                    address=account.address,
                    network="base-sepolia",
                    token="eth",
                )
            except Exception:
                pass

        local = EvmLocalAccount(account)
        state = {
            "address": account.address,
            "private_key": private_key,
            "network": "base-sepolia",
            "faucet_usdc_tx": usdc_tx,
            "faucet_eth_tx": eth_tx,
            "source": "cdp",
            "signer": "evm_local_account",
        }
        save_wallet_state(state)
        os.environ["EVM_PRIVATE_KEY"] = private_key
        os.environ["ONCHAIN_NETWORK"] = "base-sepolia"
        return {"ok": True, "account": account.address, "local_signer": local, **state}


def bootstrap_cdp_wallet() -> dict[str, Any]:
    """Create/fund CDP wallet when credentials are configured."""
    if not _has_cdp_credentials():
        existing = load_wallet_state()
        if existing and existing.get("private_key"):
            os.environ.setdefault("EVM_PRIVATE_KEY", existing["private_key"])
            os.environ.setdefault("ONCHAIN_NETWORK", existing.get("network", "base-sepolia"))
            return {"ok": True, "source": "persisted_wallet", **existing}
        return {
            "ok": False,
            "error": "Set CDP_API_KEY_ID and CDP_API_KEY_SECRET in .env (portal.cdp.coinbase.com)",
        }
    if not _has_wallet_secret():
        return {
            "ok": False,
            "error": (
                "Set CDP_WALLET_SECRET in .env — required to create/sign with CDP EVM accounts. "
                "Find it in portal.cdp.coinbase.com → API Keys → your key → Wallet Secret (shown once at creation)."
            ),
        }
    return asyncio.run(_bootstrap_cdp_async())


def get_evm_signer() -> Any:
    """Return eth_account signer or CDP EvmLocalAccount for x402."""
    from eth_account import Account

    load_dotenv()
    bootstrap = bootstrap_cdp_wallet()
    if bootstrap.get("ok") and _has_cdp_credentials():
        from cdp import CdpClient
        from cdp.evm_local_account import EvmLocalAccount

        async def _local() -> EvmLocalAccount:
            async with CdpClient() as cdp:
                account = await cdp.evm.get_or_create_account(name=CDP_ACCOUNT_NAME)
                return EvmLocalAccount(account)

        return asyncio.run(_local())

    pk = os.environ.get("EVM_PRIVATE_KEY") or (load_wallet_state() or {}).get("private_key", "")
    if not pk:
        raise RuntimeError("No EVM signer — configure CDP credentials or EVM_PRIVATE_KEY")
    return Account.from_key(pk)


def usdc_balance(address: str) -> int:
    """USDC balance (6 decimals) on Base Sepolia."""
    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider(os.environ.get("BASE_RPC_URL", "https://sepolia.base.org")))
    usdc = Web3.to_checksum_address("0x036CbD53842c5426634e7929541eC2318f3dCF7e")
    abi = [
        {
            "inputs": [{"name": "account", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        }
    ]
    contract = w3.eth.contract(address=usdc, abi=abi)
    return int(contract.functions.balanceOf(Web3.to_checksum_address(address)).call())
