"""Rollback — tier-state restore from on-Base checkpoint."""

from __future__ import annotations

import copy
from typing import Any

from ledgermind.store import GovernedMemoryClient
from onchain.checkpoint import anchor_checkpoint, load_latest_checkpoint


class RollbackManager:
    """Captures and restores governed memory snapshots with Base anchoring."""

    def __init__(self, gov: GovernedMemoryClient) -> None:
        self._gov = gov
        self._checkpoints: dict[str, dict[str, Any]] = {}

    def capture(self, label: str) -> str:
        raw = self._gov.raw
        chain_log = raw.get_state("chain:log")
        head = ""
        if chain_log:
            body = chain_log.get("body", chain_log)
            entries = body.get("entries", []) if isinstance(body, dict) else []
            if entries:
                head = entries[-1].get("hash", "")
        snapshot: dict[str, Any] = {
            "chain_log": chain_log,
            "entities": raw.list_entities(),
            "checkpoint_label": label,
            "chain_head": head,
        }
        self._checkpoints[label] = snapshot
        if head:
            anchor_checkpoint(label, head, {"entities": len(snapshot["entities"])})
        return label

    def restore(self, label: str) -> dict[str, Any]:
        if label not in self._checkpoints:
            onchain = load_latest_checkpoint(label)
            if onchain:
                return {"label": label, "restored_entities": 0, "onchain_checkpoint": onchain}
            raise KeyError(f"checkpoint not found: {label}")
        snapshot = copy.deepcopy(self._checkpoints[label])
        raw = self._gov.raw
        if snapshot.get("chain_log"):
            body = snapshot["chain_log"].get("body", snapshot["chain_log"])
            raw.set_state("chain:log", body)
        restored_entities = 0
        for ent in snapshot.get("entities", []):
            cat = ent.get("category", "")
            name = ent.get("name", "")
            body = ent.get("body", {})
            if cat and name:
                raw.set_entity(cat, name, body)
                restored_entities += 1
        self._gov.write_event(
            agent_id="governance",
            acted={"rollback": label},
            extra={"restored_entities": restored_entities, "chain_head": snapshot.get("chain_head")},
            evidence_ref=f"rollback:{label}",
        )
        return {
            "label": label,
            "restored_entities": restored_entities,
            "chain_head": snapshot.get("chain_head"),
        }
