"""Tier lifecycle promotion — dispute close path (FR-4)."""

from __future__ import annotations

from typing import Any

from ledgermind.store import GovernedMemoryClient


def promote_entity(
    gov: GovernedMemoryClient,
    *,
    kind: str,
    name: str,
    new_body: dict[str, Any],
    agent_id: str,
    dispute_id: str,
    archive_superseded: bool = True,
) -> dict[str, Any]:
    """Promote corrected fact: archive superseded → update WARM → journal COLD event."""
    if archive_superseded:
        try:
            gov.archive_entity(kind, name, agent_id=agent_id)
        except Exception:
            pass  # entity may not exist yet
    write_result = gov.set_entity(
        kind,
        name,
        new_body,
        agent_id=agent_id,
        source_trust_tier="trusted",
        evidence_ref=f"promoted:{dispute_id}",
    )
    event = gov.write_event(
        agent_id="governance",
        acted={"lifecycle": "promoted", "dispute_id": dispute_id, "entity": f"{kind}/{name}"},
        extra={"tier": "WARM"},
    )
    return {"write": write_result, "event": event}


def demote_to_archive(
    gov: GovernedMemoryClient,
    *,
    kind: str,
    name: str,
    agent_id: str,
    reason: str,
) -> None:
    gov.archive_entity(kind, name, agent_id=agent_id)
    gov.write_event(
        agent_id="governance",
        acted={"lifecycle": "archived", "entity": f"{kind}/{name}", "reason": reason},
    )
