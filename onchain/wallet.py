"""Memory-governed wallet cap enforcement via CDP + Sibyl policy (FR-6 AC-6.1)."""

from __future__ import annotations

import os
from typing import Any

from ledgermind.chain import content_hash


def read_cap_from_memory(gov: Any) -> dict[str, Any]:
    """Read wallet cap policy from Sibyl REFERENCE tier."""
    policy = gov.get_reference("policy:wallet-cap") or {}
    cap = float(policy.get("cap_usdc", 2.0))
    return {
        "policy_key": "policy:wallet-cap",
        "cap_usdc": cap,
        "content_hash": content_hash(policy) if policy else None,
        "policy": policy,
    }


def _cdp_spend_limit_usdc() -> float | None:
    """Read CDP policy spend limit when credentials are configured."""
    if not (os.environ.get("CDP_API_KEY_ID") and os.environ.get("CDP_API_KEY_SECRET")):
        return None
    try:
        import asyncio

        from cdp import CdpClient

        async def _fetch() -> float | None:
            async with CdpClient() as cdp:
                policies = await cdp.policies.list_policies()
                for policy in getattr(policies, "policies", []) or []:
                    rules = getattr(policy, "rules", None) or []
                    for rule in rules:
                        amount = getattr(rule, "max_spend_amount", None) or getattr(rule, "amount", None)
                        if amount is not None:
                            return float(amount)
            return None

        return asyncio.run(_fetch())
    except Exception:
        return None


def enforce_cap(amount_usdc: float, gov: Any) -> dict[str, Any]:
    """Refuse payments above memory-governed cap; cite policy by key + hash."""
    cap_info = read_cap_from_memory(gov)
    cap = cap_info["cap_usdc"]
    cdp_cap = _cdp_spend_limit_usdc()
    effective_cap = min(cap, cdp_cap) if cdp_cap is not None else cap
    if amount_usdc > effective_cap:
        return {
            "allowed": False,
            "reason": f"Payment ${amount_usdc:.2f} exceeds cap ${effective_cap:.2f}",
            "policy_key": cap_info["policy_key"],
            "policy_content_hash": cap_info["content_hash"],
            "cdp_cap_usdc": cdp_cap,
        }
    return {
        "allowed": True,
        "amount_usdc": amount_usdc,
        "policy_key": cap_info["policy_key"],
        "policy_content_hash": cap_info["content_hash"],
        "effective_cap_usdc": effective_cap,
        "cdp_cap_usdc": cdp_cap,
    }
