"""Dispute congress — contradiction detection and resolution protocol."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from ledgermind.config import get_settings
from ledgermind.receipts import export_public_key_b64, generate_keypair, sign_resolution
from ledgermind.store import GovernedMemoryClient
from ledgermind.verify import verify_chain


@dataclass
class DisputeRecord:
    dispute_id: str
    subject_category: str
    subject_name: str
    claimants: list[dict[str, Any]]
    evidence_refs: list[str]
    status: str
    confidence: float
    resolution: dict[str, Any] | None = None
    receipt_sig: str | None = None

    def to_body(self) -> dict[str, Any]:
        return {
            "dispute_id": self.dispute_id,
            "subject": {"category": self.subject_category, "name": self.subject_name},
            "claimants": self.claimants,
            "evidence_refs": self.evidence_refs,
            "status": self.status,
            "confidence": self.confidence,
            "resolution": self.resolution,
            "receipt_sig": self.receipt_sig,
        }


class DisputeCongress:
    """Opens disputes on contradiction; arbiter cites chain-verified records only."""

    def __init__(self, gov: GovernedMemoryClient) -> None:
        self._gov = gov
        self._private_key, self._public_key = generate_keypair()
        self._public_key_b64 = export_public_key_b64(self._public_key)

    @property
    def public_key_b64(self) -> str:
        return self._public_key_b64

    def detect_contradiction(
        self,
        existing: dict[str, Any] | None,
        incoming: dict[str, Any],
        field: str = "status",
    ) -> bool:
        if not existing:
            return False
        return existing.get(field) != incoming.get(field)

    def open_dispute(
        self,
        *,
        dispute_id: str,
        subject_category: str,
        subject_name: str,
        version_a: dict[str, Any],
        version_b: dict[str, Any],
        agent_a: str,
        agent_b: str,
        hash_a: str,
        hash_b: str,
    ) -> DisputeRecord:
        record = DisputeRecord(
            dispute_id=dispute_id,
            subject_category=subject_category,
            subject_name=subject_name,
            claimants=[
                {"agent_id": agent_a, "content_hash": hash_a, "content": version_a},
                {"agent_id": agent_b, "content_hash": hash_b, "content": version_b},
            ],
            evidence_refs=[hash_a, hash_b],
            status="open",
            confidence=0.0,
        )
        self._gov.set_entity(
            "dispute",
            dispute_id,
            record.to_body(),
            agent_id="governance",
            source_trust_tier="trusted",
            evidence_ref=f"dispute:{dispute_id}",
        )
        return record

    def verify_citations(self, citations: list[dict[str, Any]]) -> bool:
        for cite in citations:
            tree = cite.get("tree", "")
            entries = self._gov.get_chain_entries(tree)
            result = verify_chain(tree, entries)
            if not result.ok:
                return False
        return True

    def arbitrate(
        self,
        dispute: DisputeRecord,
        *,
        winning_claimant_idx: int,
        citations: list[dict[str, Any]],
        confidence: float,
        arbiter_reasoning: str = "",
        arbiter_backend: str = "rule-based",
    ) -> DisputeRecord:
        if not self.verify_citations(citations):
            raise ValueError("citation verification failed — arbiter may cite only chain-verified records")
        winner = dispute.claimants[winning_claimant_idx]
        dispute.status = "arbiter"
        dispute.confidence = confidence
        dispute.resolution = {
            "winner_agent": winner["agent_id"],
            "winner_hash": winner["content_hash"],
            "citations": citations,
            "arbiter_backend": arbiter_backend,
            "arbiter_reasoning": arbiter_reasoning,
        }
        return dispute

    def _format_dispute_prompt(self, dispute: DisputeRecord, citations: list[dict[str, Any]]) -> str:
        claimants = json.dumps(dispute.claimants, indent=2)
        cites = json.dumps(citations, indent=2)
        return (
            "You are the dispute arbiter for a governed agent-memory system.\n"
            "You may cite ONLY the chain-verified records listed in citations.\n"
            f"Dispute ID: {dispute.dispute_id}\n"
            f"Subject: {dispute.subject_category}/{dispute.subject_name}\n"
            f"Claimants:\n{claimants}\n"
            f"Verified citations:\n{cites}\n"
            'Reply with JSON only: {"winner_agent": "<agent_id>", "confidence": 0.0-1.0, "reasoning": "..."}'
        )

    def _parse_arbiter_response(
        self,
        dispute: DisputeRecord,
        text: str,
        *,
        fallback_idx: int,
    ) -> tuple[int, float, str]:
        reasoning = text.strip()
        try:
            match = re.search(r"\{[\s\S]*\}", text)
            payload = json.loads(match.group(0) if match else text)
            winner_agent = str(payload.get("winner_agent", "")).strip()
            confidence = float(payload.get("confidence", 0.9))
            reasoning = str(payload.get("reasoning", reasoning))
            for idx, claimant in enumerate(dispute.claimants):
                if claimant["agent_id"] == winner_agent:
                    return idx, confidence, reasoning
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        lowered = text.lower()
        for idx, claimant in enumerate(dispute.claimants):
            if claimant["agent_id"].lower() in lowered:
                return idx, 0.9, reasoning
        return fallback_idx, 0.85, reasoning

    def arbitrate_with_vertex(
        self,
        dispute: DisputeRecord,
        *,
        citations: list[dict[str, Any]],
        fallback_winner_idx: int = 1,
        confidence: float | None = None,
        use_vertex: bool = True,
    ) -> tuple[DisputeRecord, dict[str, Any]]:
        """Run Gemini arbiter with thinking_level=high; fall back to rule-based if Vertex unavailable."""
        settings = get_settings()
        meta: dict[str, Any] = {
            "backend": "rule-based",
            "model": settings.model_arbiter,
            "reasoning": "",
        }
        winner_idx = fallback_winner_idx
        resolved_confidence = confidence if confidence is not None else 0.85

        if use_vertex and settings.google_cloud_project:
            try:
                from ledgermind.vertex import generate_content

                prompt = self._format_dispute_prompt(dispute, citations)
                reasoning = generate_content(settings.model_arbiter, prompt, thinking_high=True)
                winner_idx, parsed_conf, parsed_reason = self._parse_arbiter_response(
                    dispute,
                    reasoning,
                    fallback_idx=fallback_winner_idx,
                )
                resolved_confidence = confidence if confidence is not None else parsed_conf
                meta = {
                    "backend": "vertex",
                    "model": settings.model_arbiter,
                    "reasoning": parsed_reason,
                }
            except Exception as exc:
                meta["backend"] = "rule-based"
                meta["vertex_error"] = str(exc)

        dispute = self.arbitrate(
            dispute,
            winning_claimant_idx=winner_idx,
            citations=citations,
            confidence=resolved_confidence,
            arbiter_reasoning=meta.get("reasoning", ""),
            arbiter_backend=meta["backend"],
        )
        return dispute, meta

    def await_human_gate(
        self,
        dispute: DisputeRecord,
        *,
        approved: bool,
        approver: str = "operator",
    ) -> DisputeRecord:
        settings = get_settings()
        if dispute.confidence < settings.human_gate_threshold:
            if not approved:
                dispute.status = "awaiting_human"
                return dispute
            self._gov.write_event(
                agent_id="governance",
                acted={"human_gate": "approved", "approver": approver},
                extra={"dispute_id": dispute.dispute_id, "confidence": dispute.confidence},
            )
        dispute.status = "resolved"
        payload = {
            "dispute_id": dispute.dispute_id,
            "resolution": dispute.resolution,
            "public_key": self._public_key_b64,
        }
        dispute.receipt_sig = sign_resolution(self._private_key, payload)
        self._gov.set_reference(
            f"receipt:{dispute.dispute_id}",
            {**payload, "receipt_sig": dispute.receipt_sig},
            agent_id="governance",
            evidence_ref=f"receipt:{dispute.dispute_id}",
        )
        return dispute

    def promote_resolution(
        self,
        dispute: DisputeRecord,
        *,
        subject_kind: str,
        agent_id: str,
    ) -> None:
        if not dispute.resolution:
            raise ValueError("dispute not resolved")
        winner = next(
            c for c in dispute.claimants if c["agent_id"] == dispute.resolution["winner_agent"]
        )
        self._gov.archive_entity(subject_kind, dispute.subject_name, agent_id=agent_id)
        self._gov.set_entity(
            subject_kind,
            dispute.subject_name,
            winner["content"],
            agent_id=agent_id,
            source_trust_tier="trusted",
            evidence_ref=f"promoted:{dispute.dispute_id}",
        )
        self._gov.write_event(
            agent_id="governance",
            acted={"lifecycle": "promoted", "dispute_id": dispute.dispute_id},
            extra={"subject": dispute.subject_name},
        )
