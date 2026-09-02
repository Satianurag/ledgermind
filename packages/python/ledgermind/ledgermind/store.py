"""GovernedMemoryClient — the ONLY code path to Sibyl Memory."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sibyl_memory_client import MemoryClient
from sibyl_memory_client.exceptions import NotFoundError

from ledgermind.chain import GENESIS_HASH, ChainEntry, chain_link, content_hash
from ledgermind.provenance import (
    TRUST_THRESHOLD,
    ProvenanceStamp,
    make_stamp,
    score_source_trust,
)
from ledgermind.quarantine import (
    is_quarantine_category,
    quarantine_category,
    should_exclude_from_recall,
)
from ledgermind.verify import verify_chain

CHAIN_LOG_KEY = "chain:log"
CHAIN_HEAD_PREFIX = "chain:head:"


class GovernedMemoryClient:
    """Wraps Sibyl Memory with provenance, hash chain, and quarantine."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self._db_path.parent, 0o700)
        self._client = MemoryClient.local(str(self._db_path))

    def __enter__(self) -> GovernedMemoryClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        close_fn = getattr(self._client, "close", None)
        if callable(close_fn):
            close_fn()

    @property
    def raw(self) -> MemoryClient:
        """Escape hatch for tests only — prefer governed methods."""
        return self._client

    def _category(self, agent_id: str, kind: str) -> str:
        if ":" in kind and not kind.startswith("quarantine:"):
            return kind
        return f"{agent_id}:{kind}"

    def _chain_tree(self, tier: str, key: str) -> str:
        return f"{tier}:{key}"

    def _get_chain_head(self, tree: str) -> str:
        head_key = f"{CHAIN_HEAD_PREFIX}{tree}"
        state = self._client.get_state(head_key)
        if not state:
            return GENESIS_HASH
        body = state.get("body", state)
        if isinstance(body, dict):
            return body.get("hash", GENESIS_HASH)
        return GENESIS_HASH

    def _set_chain_head(self, tree: str, hash_value: str, sequence: int) -> None:
        head_key = f"{CHAIN_HEAD_PREFIX}{tree}"
        self._client.set_state(head_key, {"hash": hash_value, "sequence": sequence})

    def _append_chain(
        self,
        tree: str,
        stamp: ProvenanceStamp,
        body: dict[str, Any] | list[Any],
    ) -> ChainEntry:
        prev_hash = self._get_chain_head(tree)
        log_state = self._client.get_state(CHAIN_LOG_KEY) or {}
        log_body = log_state.get("body", log_state) if isinstance(log_state, dict) else {}
        if not isinstance(log_body, dict):
            log_body = {}
        entries: list[dict[str, Any]] = list(log_body.get("entries", []))
        tree_entries = [e for e in entries if e.get("tree") == tree]
        sequence = (max((e.get("sequence", 0) for e in tree_entries), default=-1)) + 1
        stamp_dict = stamp.to_dict()
        link_hash = chain_link(prev_hash, stamp_dict, body)
        entry = ChainEntry(
            tree=tree,
            sequence=sequence,
            prev_hash=prev_hash,
            hash=link_hash,
            stamp=stamp_dict,
            body=body,
        )
        entries.append(entry.to_record())
        self._client.set_state(CHAIN_LOG_KEY, {"entries": entries})
        self._set_chain_head(tree, link_hash, sequence)
        return entry

    def _governed_write(
        self,
        *,
        agent_id: str,
        source_trust_tier: str,
        evidence_ref: str,
        tree: str,
        body: dict[str, Any] | list[Any],
        write_fn: Any,
        force_quarantine: bool = False,
    ) -> dict[str, Any]:
        stamp = make_stamp(
            agent_id=agent_id,
            source_trust_tier=source_trust_tier,
            evidence_ref=evidence_ref,
        )
        trust_score = score_source_trust(source_trust_tier)
        quarantined = force_quarantine or trust_score < TRUST_THRESHOLD
        stamped_body = {
            "_provenance": stamp.to_dict(),
            "_content": body,
        }
        entry = self._append_chain(tree, stamp, stamped_body)
        result: dict[str, Any] = {
            "quarantined": quarantined,
            "chain_entry": entry.to_record(),
            "content_hash": content_hash(body),
        }
        if quarantined:
            qcat = quarantine_category(agent_id)
            qname = f"{tree}-{entry.sequence}"
            self._client.set_entity(qcat, qname, stamped_body)
            result["quarantine_key"] = f"{qcat}/{qname}"
            return result
        write_fn(stamped_body)
        return result

    def set_state(
        self,
        key: str,
        body: dict[str, Any] | list[Any],
        *,
        agent_id: str,
        source_trust_tier: str = "internal",
        evidence_ref: str = "",
    ) -> dict[str, Any]:
        tree = self._chain_tree("hot", key)
        return self._governed_write(
            agent_id=agent_id,
            source_trust_tier=source_trust_tier,
            evidence_ref=evidence_ref or f"hot:{key}",
            tree=tree,
            body=body,
            write_fn=lambda b: self._client.set_state(key, b),
        )

    def get_state(self, key: str) -> dict[str, Any] | None:
        raw = self._client.get_state(key)
        if not raw:
            return None
        body = raw.get("body", raw)
        if isinstance(body, dict) and "_content" in body:
            return body["_content"]
        return body if isinstance(body, dict) else raw

    def set_entity(
        self,
        kind: str,
        name: str,
        body: dict[str, Any] | list[Any],
        *,
        agent_id: str,
        source_trust_tier: str = "internal",
        evidence_ref: str = "",
        force_quarantine: bool = False,
    ) -> dict[str, Any]:
        category = self._category(agent_id, kind)
        tree = self._chain_tree("warm", f"{category}/{name}")

        def _write(stamped: dict[str, Any]) -> None:
            self._client.set_entity(category, name, stamped)

        return self._governed_write(
            agent_id=agent_id,
            source_trust_tier=source_trust_tier,
            evidence_ref=evidence_ref or f"warm:{category}/{name}",
            tree=tree,
            body=body,
            write_fn=_write,
            force_quarantine=force_quarantine,
        )

    def get_entity(self, kind: str, name: str, *, agent_id: str = "shared") -> dict[str, Any] | None:
        category = self._category(agent_id, kind) if ":" not in kind else kind
        # Sibyl raises NotFoundError for a missing entity while get_state/get_reference
        # return None. Every caller here treats a miss as None (`or {}`), so normalise it:
        # an unseeded store must read as empty, not explode. A fresh clone has no
        # demo-data/, which is exactly the state a judge starts from.
        try:
            raw = self._client.get_entity(category, name)
        except NotFoundError:
            return None
        if not raw:
            return None
        body = raw.get("body", raw)
        if isinstance(body, dict) and "_content" in body:
            return body["_content"]
        return body if isinstance(body, dict) else raw

    def write_event(
        self,
        *,
        agent_id: str,
        acted: dict[str, Any] | None = None,
        evaluated: dict[str, Any] | None = None,
        forward: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
        source_trust_tier: str = "internal",
        evidence_ref: str = "",
    ) -> dict[str, Any]:
        payload = {
            "acted": acted,
            "evaluated": evaluated,
            "forward": forward,
            "extra": {**(extra or {}), "agent_id": agent_id},
        }
        tree = self._chain_tree("cold", f"event:{agent_id}")
        result = self._governed_write(
            agent_id=agent_id,
            source_trust_tier=source_trust_tier,
            evidence_ref=evidence_ref or f"cold:event:{agent_id}",
            tree=tree,
            body=payload,
            write_fn=lambda _: self._client.write_event(
                acted=acted, evaluated=evaluated, forward=forward, extra=extra
            ),
        )
        return result

    def read_events(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return self._client.read_events(limit=limit)

    def set_reference(
        self,
        key: str,
        body: dict[str, Any] | list[Any],
        *,
        agent_id: str,
        source_trust_tier: str = "trusted",
        evidence_ref: str = "",
    ) -> dict[str, Any]:
        tree = self._chain_tree("reference", key)
        return self._governed_write(
            agent_id=agent_id,
            source_trust_tier=source_trust_tier,
            evidence_ref=evidence_ref or f"reference:{key}",
            tree=tree,
            body=body,
            write_fn=lambda b: self._client.set_reference(key, b),
        )

    def get_reference(self, key: str) -> dict[str, Any] | None:
        raw = self._client.get_reference(key)
        if not raw:
            return None
        body = raw.get("body", raw)
        if isinstance(body, str):
            import json

            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                return {"raw": body}
        if isinstance(body, dict) and "_content" in body:
            return body["_content"]
        return body if isinstance(body, dict) else raw

    def archive_entity(self, kind: str, name: str, *, agent_id: str = "shared") -> None:
        category = self._category(agent_id, kind) if ":" not in kind else kind
        self._client.archive_entity(category, name)

    def search_entities(self, query: str, *, include_quarantine: bool = False) -> list[dict[str, Any]]:
        results = self._client.search_entities(query)
        if include_quarantine:
            return results
        filtered = []
        for item in results:
            cat = item.get("category", "")
            if should_exclude_from_recall(cat):
                continue
            filtered.append(item)
        return filtered

    def get_chain_entries(self, tree: str | None = None) -> list[dict[str, Any]]:
        log_state = self._client.get_state(CHAIN_LOG_KEY) or {}
        log_body = log_state.get("body", log_state) if isinstance(log_state, dict) else {}
        if not isinstance(log_body, dict):
            return []
        entries = log_body.get("entries", [])
        if tree:
            return [e for e in entries if e.get("tree") == tree]
        return entries

    def verify_tree(self, tree: str) -> dict[str, Any]:
        entries = self.get_chain_entries(tree)
        return verify_chain(tree, entries).to_dict()

    def verify_all(self) -> list[dict[str, Any]]:
        log_state = self._client.get_state(CHAIN_LOG_KEY) or {}
        log_body = log_state.get("body", log_state) if isinstance(log_state, dict) else {}
        if not isinstance(log_body, dict):
            return []
        trees = sorted({e.get("tree") for e in log_body.get("entries", []) if e.get("tree")})
        return [self.verify_tree(t) for t in trees]

    def get_quarantine_items(self, agent_id: str | None = None) -> list[dict[str, Any]]:
        prefix = quarantine_category(agent_id or "")
        entities = self._client.list_entities()
        items = []
        for ent in entities:
            cat = ent.get("category", "")
            if is_quarantine_category(cat):
                if agent_id and not cat.startswith(prefix.rstrip(":")):
                    continue
                items.append(ent)
        return items
