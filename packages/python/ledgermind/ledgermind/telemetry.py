"""Decision-impact telemetry and counterfactual replay."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ledgermind.chain import content_hash
from ledgermind.store import GovernedMemoryClient

TELEMETRY_DIR = Path(__file__).resolve().parents[3] / "demo-data" / "telemetry"


@dataclass
class Citation:
    key: str
    content_hash: str
    chain_seq: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "content_hash": self.content_hash,
            "chain_seq": self.chain_seq,
        }


@dataclass
class DecisionLogEntry:
    decision_id: str
    agent: str
    ts: str
    citations: list[Citation] = field(default_factory=list)
    outcome: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "agent": self.agent,
            "ts": self.ts,
            "citations": [c.to_dict() for c in self.citations],
            "outcome": self.outcome,
        }


class TelemetryLogger:
    """Citation log: memory item hash → decision."""

    MANIFEST_KEY = "telemetry:manifest"

    def __init__(self, gov: GovernedMemoryClient) -> None:
        self._gov = gov
        self._entries: list[DecisionLogEntry] = []

    def log_decision(
        self,
        *,
        agent: str,
        citations: list[Citation],
        outcome: str,
        ts: str,
    ) -> DecisionLogEntry:
        entry = DecisionLogEntry(
            decision_id=str(uuid.uuid4()),
            agent=agent,
            ts=ts,
            citations=citations,
            outcome=outcome,
        )
        self._entries.append(entry)
        self._gov.set_reference(
            f"telemetry:decision:{entry.decision_id}",
            entry.to_dict(),
            agent_id="governance",
        )
        return entry

    def counterfactual_replay(
        self,
        decision_fn: Callable[[dict[str, Any]], str],
        context: dict[str, Any],
        *,
        remove_key: str,
    ) -> dict[str, Any]:
        baseline = decision_fn(context)
        modified = {k: v for k, v in context.items() if k != remove_key}
        counter = decision_fn(modified)
        flipped = baseline != counter

        # Cite the removed item by its real content hash. The on-screen panel is the
        # evidence that a specific remembered record caused the decision, so a
        # placeholder key name is not enough.
        removed = context.get(remove_key)
        removed_hash = (
            content_hash(removed) if isinstance(removed, (dict, list)) and removed else None
        )
        short = removed_hash[:16] if removed_hash else remove_key
        return {
            "baseline": baseline,
            "counterfactual": counter,
            "flipped": flipped,
            "removed_key": remove_key,
            "removed_content_hash": removed_hash,
            "explanation": (
                f"Removing memory item {short} ({remove_key}) changes the decision "
                f"from '{baseline}' to '{counter}'."
                if flipped
                else f"Decision is stable without {remove_key} ('{baseline}')."
            ),
        }

    def build_citation(self, key: str, body: dict[str, Any]) -> Citation:
        return Citation(key=key, content_hash=content_hash(body))

    def get_entries(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._entries]

    def save_manifest(self, *, run_id: str, versions: dict[str, str]) -> None:
        manifest = {"run_id": run_id, "versions": versions, "entries": self.get_entries()}
        self._gov.set_reference(
            self.MANIFEST_KEY,
            manifest,
            agent_id="governance",
        )
        self._export_jsonl(manifest)

    def _export_jsonl(self, manifest: dict[str, Any]) -> None:
        """Persist telemetry manifest to JSONL (Langfuse-compatible offline fallback)."""
        TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
        path = TELEMETRY_DIR / "decision_impact.jsonl"
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "decision_impact_manifest",
            "manifest": manifest,
            "langfuse_host": os.environ.get("LANGFUSE_HOST"),
        }
        with path.open("a") as f:
            f.write(json.dumps(record) + "\n")
        self._maybe_push_langfuse(manifest)

    def _maybe_push_langfuse(self, manifest: dict[str, Any]) -> None:
        public = os.environ.get("LANGFUSE_PUBLIC_KEY")
        secret = os.environ.get("LANGFUSE_SECRET_KEY")
        host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000")
        if not (public and secret):
            return
        try:
            import httpx

            httpx.post(
                f"{host.rstrip('/')}/api/public/ingestion",
                json={"batch": [{"type": "trace-create", "body": {"name": "ledgermind", "metadata": manifest}}]},
                auth=(public, secret),
                timeout=10,
            )
        except Exception:
            pass
