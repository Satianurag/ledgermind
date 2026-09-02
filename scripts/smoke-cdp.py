"""Quick CDP credential smoke test (no wallet creation)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def _run() -> int:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    key_id = os.environ.get("CDP_API_KEY_ID", "")
    key_secret = os.environ.get("CDP_API_KEY_SECRET", "")
    wallet_secret = os.environ.get("CDP_WALLET_SECRET", "")

    print(f"CDP_API_KEY_ID: {'set' if key_id else 'MISSING'}")
    print(f"CDP_API_KEY_SECRET: {'set' if key_secret else 'MISSING'}")
    print(f"CDP_WALLET_SECRET: {'set' if wallet_secret else 'MISSING (needed for EVM account create)'}")

    if not (key_id and key_secret):
        return 1

    from cdp import CdpClient

    async with CdpClient() as cdp:
        accounts = await cdp.api_clients.evm_accounts.list_evm_accounts()
        print(f"Auth OK — list_evm_accounts returned {len(accounts.accounts or [])} account(s)")

    if not wallet_secret:
        print("\nNext step: add CDP_WALLET_SECRET to .env, then run make bootstrap-onchain")
        return 2

    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
