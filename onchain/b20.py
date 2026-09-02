"""B20 tokenized stock reads on Base (PRD §6.6 FR-6)."""

from __future__ import annotations

import os
from typing import Any

from web3 import Web3

from onchain.network import B20_RPC_URL, load_network_env

ACTIVATION_REGISTRY = "0x8453000000000000000000000000000000000001"
# COINc tokenized stock on Base mainnet (docs.base.org B20 tokenized stocks)
DEFAULT_B20_TOKEN = "0xb200000000000000000000c85a31389D71F3ecfb"

ERC20_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "multiplier",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "contractURI",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
]

REGISTRY_ABI = [
    {
        "inputs": [{"name": "featureId", "type": "bytes32"}],
        "name": "isActivated",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    }
]


def _rpc_url() -> str:
    load_network_env()
    # B20 tokenized stocks are mainnet-only — never use Sepolia BASE_RPC_URL here.
    return os.environ.get("B20_RPC_URL", B20_RPC_URL)


def _w3() -> Web3:
    w3 = Web3(Web3.HTTPProvider(_rpc_url()))
    if not w3.is_connected():
        raise ConnectionError(f"cannot connect to Base RPC: {_rpc_url()}")
    return w3


def read_b20(
    token_address: str | None = None,
    holder: str | None = None,
) -> dict[str, Any]:
    """Live B20 read: isActivated, balanceOf, multiplier, contractURI."""
    w3 = _w3()
    token = Web3.to_checksum_address(token_address or DEFAULT_B20_TOKEN)
    holder_addr = Web3.to_checksum_address(
        holder or "0x0000000000000000000000000000000000000001"
    )
    registry = w3.eth.contract(
        address=Web3.to_checksum_address(ACTIVATION_REGISTRY),
        abi=REGISTRY_ABI,
    )
    b20_feature = w3.keccak(text="base.b20_asset")
    activated = registry.functions.isActivated(b20_feature).call()

    token_contract = w3.eth.contract(address=token, abi=ERC20_ABI)
    balance = token_contract.functions.balanceOf(holder_addr).call()
    multiplier = token_contract.functions.multiplier().call()
    uri = token_contract.functions.contractURI().call()

    explorer = "https://basescan.org"
    return {
        "kind": "b20",
        "activated": activated,
        "token": token,
        "holder": holder_addr,
        "balanceOf": str(balance),
        "multiplier": str(multiplier),
        "contractURI": uri,
        "explorer_url": f"{explorer}/token/{token}",
        "rpc": _rpc_url(),
        "source": "live",
    }
