"""Onchain network defaults — Base Sepolia for all settlement; B20 read-only on mainnet."""

from __future__ import annotations

import os

from dotenv import load_dotenv

# Settlement stack (wallet, x402, ACP, checkpoints)
DEFAULT_NETWORK = "base-sepolia"
DEFAULT_CHAIN_ID = 84532
DEFAULT_RPC_URL = "https://sepolia.base.org"
DEFAULT_EXPLORER = "https://sepolia.basescan.org"

# B20 tokenized stocks are mainnet-only (PRD §6.6 O4)
B20_RPC_URL = "https://mainnet.base.org"

# Virtuals ACP testnet toggle (separate config file: ~/.config/acp/config-testnet.json)
ACP_TESTNET = True


def load_network_env() -> None:
    """Apply testnet-first defaults from .env without overriding explicit values."""
    load_dotenv()
    os.environ.setdefault("ONCHAIN_NETWORK", DEFAULT_NETWORK)
    os.environ.setdefault("BASE_RPC_URL", DEFAULT_RPC_URL)
    os.environ.setdefault("B20_RPC_URL", B20_RPC_URL)
    os.environ.setdefault("ACP_CHAIN_ID", str(DEFAULT_CHAIN_ID))
    if ACP_TESTNET or os.environ.get("IS_TESTNET", "").lower() in ("1", "true", "yes"):
        os.environ["IS_TESTNET"] = "true"
    else:
        os.environ.setdefault("IS_TESTNET", "false")


def explorer_tx_url(tx_hash: str) -> str:
    network = os.environ.get("ONCHAIN_NETWORK", DEFAULT_NETWORK)
    base = DEFAULT_EXPLORER if "sepolia" in network else "https://basescan.org"
    return f"{base}/tx/{tx_hash}"


def acp_subprocess_env() -> dict[str, str]:
    load_network_env()
    return os.environ.copy()
