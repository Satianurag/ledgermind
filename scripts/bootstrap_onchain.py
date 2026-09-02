"""Bootstrap onchain settlement: CDP wallet + faucet + x402 + ACP + checkpoint."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from dotenv import load_dotenv

    from onchain.network import load_network_env

    load_dotenv(ROOT / ".env")
    load_network_env()

    from onchain.cdp_wallet import _has_cdp_credentials, bootstrap_cdp_wallet

    if not _has_cdp_credentials():
        print(
            "ERROR: CDP_API_KEY_ID and CDP_API_KEY_SECRET required for live settlement.\n"
            "Create keys at https://portal.cdp.coinbase.com → API Keys → copy to .env"
        )
        return 1

    wallet = bootstrap_cdp_wallet()
    if not wallet.get("ok"):
        print("Wallet bootstrap failed:", wallet.get("error", wallet))
        return 1

    print("Funded wallet:", wallet.get("address"))
    from scripts.prerun_settlement import main as prerun_main

    return prerun_main()


if __name__ == "__main__":
    raise SystemExit(main())
