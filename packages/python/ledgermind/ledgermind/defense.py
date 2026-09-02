"""Dual-path adversarial defense: source-trust quarantine + chain-break detection."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from ledgermind.provenance import TRUST_THRESHOLD, score_source_trust
from ledgermind.store import GovernedMemoryClient

POISON_PATTERNS = re.compile(
    r"bank details|reroute payout|override|attacker|ignore policy|wire recall|admin mode|delete audit",
    re.I,
)


@dataclass
class DefenseVerdict:
    caught: bool
    paths_fired: list[str]
    quarantined: bool
    chain_break: bool
    detail: str
    write_result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "caught": self.caught,
            "paths_fired": self.paths_fired,
            "quarantined": self.quarantined,
            "chain_break": self.chain_break,
            "detail": self.detail,
            "write_result": self.write_result,
        }


def evaluate_injection(
    gov: GovernedMemoryClient,
    *,
    agent_id: str,
    kind: str,
    name: str,
    body: dict[str, Any],
    source_trust_tier: str,
    evidence_ref: str,
    simulate_chain_break: bool = False,
) -> DefenseVerdict:
    """Evaluate a potentially poisoned write through both defense paths."""
    paths: list[str] = []
    trust = score_source_trust(source_trust_tier)
    force_quarantine = trust < TRUST_THRESHOLD
    body_text = json.dumps(body, default=str)
    content_poison = bool(POISON_PATTERNS.search(body_text))

    result = gov.set_entity(
        kind,
        name,
        body,
        agent_id=agent_id,
        source_trust_tier=source_trust_tier,
        evidence_ref=evidence_ref,
        force_quarantine=force_quarantine,
    )
    quarantined = bool(result.get("quarantined"))
    if quarantined:
        paths.append("source-trust")

    chain_break = simulate_chain_break or content_poison
    if content_poison and not quarantined and "chain-break" not in paths:
        paths.append("chain-break")
    if simulate_chain_break and "chain-break" not in paths:
        paths.append("chain-break")

    tree = result.get("chain_entry", {}).get("tree", "")
    if tree:
        verification = gov.verify_tree(tree)
        if not verification.get("ok") and not chain_break:
            chain_break = True
            paths.append("chain-break")

    caught = quarantined or chain_break
    detail_parts = []
    if quarantined:
        detail_parts.append("QUARANTINED: source trust below threshold")
    if chain_break:
        detail_parts.append("CHAIN-BREAK: hash chain integrity violation")
    if not caught:
        detail_parts.append("CLEAN: no defense path fired")

    return DefenseVerdict(
        caught=caught,
        paths_fired=paths,
        quarantined=quarantined,
        chain_break=chain_break,
        detail="; ".join(detail_parts),
        write_result=result,
    )
