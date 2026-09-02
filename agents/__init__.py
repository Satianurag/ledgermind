"""LangGraph agent definitions — planner, worker, auditor, arbiter."""

from __future__ import annotations

from typing import Any

from ledgermind.config import get_settings
from ledgermind.store import GovernedMemoryClient
from ledgermind.vertex import generate_content


class BaseAgent:
    """Agent that reads/writes only through governance layer."""

    def __init__(self, gov: GovernedMemoryClient, agent_id: str) -> None:
        self.gov = gov
        self.agent_id = agent_id

    def write_assignment(self, case_id: str, task: str) -> dict[str, Any]:
        return self.gov.set_state(
            "priorities",
            {"case": case_id, "task": task},
            agent_id=self.agent_id,
            evidence_ref=f"{self.agent_id}:assignment",
        )

    def record_action(self, action: dict[str, Any]) -> dict[str, Any]:
        return self.gov.write_event(
            agent_id=self.agent_id,
            acted=action,
            evidence_ref=f"{self.agent_id}:action",
        )


class PlannerAgent(BaseAgent):
    """Atlas — assigns work."""

    def plan(self, case_id: str) -> str:
        settings = get_settings()
        prompt = f"As planner Atlas, assign resolution for {case_id}. One sentence."
        return generate_content(settings.model_planner, prompt)


class WorkerAgent(BaseAgent):
    """Vesper — executes payout actions."""

    def execute(self, case_id: str, action: str) -> dict[str, Any]:
        return self.record_action({"case": case_id, "payout": action})


class AuditorAgent(BaseAgent):
    """Kestrel — policy checks."""

    def audit(self, amount_usd: float) -> dict[str, Any]:
        policy = self.gov.get_reference("policy:vendor-payout") or {}
        threshold = policy.get("dual_approval_threshold_usd", 10000)
        return {
            "passed": True,
            "requires_dual_approval": amount_usd > threshold,
            "policy": policy,
        }


class ArbiterAgent:
    """Resolves disputes citing chain-verified records only."""

    def __init__(self, gov: GovernedMemoryClient) -> None:
        self.gov = gov

    def resolve(self, dispute_summary: str) -> str:
        settings = get_settings()
        chains = self.gov.verify_all()
        verified = [c for c in chains if c.get("ok")]
        prompt = (
            f"Arbiter verdict for dispute: {dispute_summary}\n"
            f"Chain-verified trees: {len(verified)}\n"
            f"Cite only verified records. One paragraph resolution."
        )
        return generate_content(settings.model_arbiter, prompt, thinking_high=True)


def run_agent_smoke(gov: GovernedMemoryClient) -> dict[str, Any]:
    planner = PlannerAgent(gov, "planner")
    worker = WorkerAgent(gov, "worker")
    auditor = AuditorAgent(gov, "auditor")
    planner.write_assignment("CASE-2214", "resolve before Sep 9")
    worker.execute("CASE-2214", "held")
    audit = auditor.audit(12400)
    return {"audit": audit, "agents": ["atlas", "vesper", "kestrel"]}
