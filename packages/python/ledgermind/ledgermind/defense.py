"""Write-path defense: source-trust quarantine, chain integrity, content heuristic.

Naming here is deliberate, because an earlier version of this module reported a keyword
regex match as a "chain-break". It was not one: no chain was consulted. Three independent
signals, each reported as what it actually is:

  source-trust       provenance tier below threshold -> quarantine. Real, but it only
                     knows what the caller declares. An attacker writing through an
                     untrusted channel is caught; an attacker who has compromised a
                     trusted one is not.
  chain-integrity    fires only when verify_chain() genuinely fails on the written tree.
                     This is the tamper-evidence path and it never fires on content.
  content-heuristic  a small keyword screen. It is reported separately and deliberately
                     NOT treated as a defense in the eval harness, because content
                     screening cannot detect a plainly-worded false assertion: arXiv
                     2608.21230 screened 360 poisoned memories on a four-stage pipeline
                     and refused zero of them. It is kept for demo legibility, not as
                     evidence, and `caught` does not depend on it.

The load-bearing defense in this project is not any of these three. It is that a
contradiction opens a dispute instead of overwriting the prior record -- see dispute.py.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from ledgermind.provenance import TRUST_THRESHOLD, score_source_trust
from ledgermind.store import GovernedMemoryClient

# Illustrative only. See the module docstring: this is not counted as a defense.
CONTENT_HEURISTIC_PATTERNS = re.compile(
    r"bank details|reroute payout|override|attacker|ignore policy|wire recall|"
    r"admin mode|delete audit",
    re.I,
)


@dataclass
class DefenseVerdict:
    caught: bool
    paths_fired: list[str]
    quarantined: bool
    chain_break: bool
    detail: str
    content_flag: bool = False
    write_result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "caught": self.caught,
            "paths_fired": self.paths_fired,
            "quarantined": self.quarantined,
            "chain_break": self.chain_break,
            "content_flag": self.content_flag,
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
    """Evaluate a write against each defense path, reporting them independently."""
    paths: list[str] = []
    trust = score_source_trust(source_trust_tier)
    force_quarantine = trust < TRUST_THRESHOLD

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

    # Chain integrity is decided by re-walking the chain, never by inspecting content.
    chain_break = bool(simulate_chain_break)
    tree = result.get("chain_entry", {}).get("tree", "")
    if tree and not gov.verify_tree(tree).get("ok"):
        chain_break = True
    if chain_break:
        paths.append("chain-integrity")

    # Reported, never counted.
    content_flag = bool(CONTENT_HEURISTIC_PATTERNS.search(json.dumps(body, default=str)))
    if content_flag:
        paths.append("content-heuristic")

    caught = quarantined or chain_break

    detail_parts = []
    if quarantined:
        detail_parts.append("QUARANTINED: source trust below threshold")
    if chain_break:
        detail_parts.append("CHAIN-INTEGRITY: hash chain verification failed")
    if content_flag:
        detail_parts.append("CONTENT-HEURISTIC: keyword match (advisory only)")
    if not caught:
        detail_parts.append("CLEAN: no defense path fired")

    return DefenseVerdict(
        caught=caught,
        paths_fired=paths,
        quarantined=quarantined,
        chain_break=chain_break,
        content_flag=content_flag,
        detail="; ".join(detail_parts),
        write_result=result,
    )
