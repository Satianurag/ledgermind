"""Provenance stamping for governance-relevant writes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ProvenanceStamp:
    agent_id: str
    timestamp: str
    source_trust_tier: str
    evidence_ref: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_stamp(
    *,
    agent_id: str,
    source_trust_tier: str,
    evidence_ref: str,
    timestamp: str | None = None,
) -> ProvenanceStamp:
    return ProvenanceStamp(
        agent_id=agent_id,
        timestamp=timestamp or utc_now_iso(),
        source_trust_tier=source_trust_tier,
        evidence_ref=evidence_ref,
    )


def score_source_trust(source_trust_tier: str) -> float:
    """Map trust tier labels to numeric scores for quarantine decisions."""
    tiers = {
        "trusted": 1.0,
        "internal": 0.9,
        "verified": 0.85,
        "external": 0.5,
        "unknown": 0.2,
        "hostile": 0.0,
    }
    return tiers.get(source_trust_tier.lower(), 0.2)


TRUST_THRESHOLD = 0.6
