"""LangGraph agent graph wiring (PRD §6.3).

Every value the agents act on is read back out of Sibyl. Nothing here restates the case
file from a literal: the payout amount comes from the WARM case entity, the approval
threshold from the REFERENCE policy, and the contradiction that opens the dispute is
*detected* by comparing two COLD journal records rather than being scripted. Delete the
memory and each node loses the input it needs, which is the point of the deletion test.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from ledgermind.dispute import DisputeCongress
from ledgermind.store import GovernedMemoryClient

DEFAULT_CASE_ID = "CASE-2214"


class AgentState(TypedDict, total=False):
    case_id: str
    messages: list[str]
    case: dict[str, Any]
    policy: dict[str, Any]
    audit: dict[str, Any]
    dispute: dict[str, Any] | None
    contradiction: bool
    recalled_from_memory: bool
    outcome: str


def _say(state: AgentState, message: str) -> list[str]:
    return state.get("messages", []) + [message]


def build_demo_graph(gov: GovernedMemoryClient, *, use_vertex: bool = False):
    """Three-agent reference topology: planner -> worker -> auditor -> reconcile.

    `use_vertex` drives the planner through Gemini. It defaults to False so tests and CI
    stay hermetic; the demo turns it on.
    """

    def planner_node(state: AgentState) -> AgentState:
        from agents import PlannerAgent

        case_id = state.get("case_id", DEFAULT_CASE_ID)
        agent = PlannerAgent(gov, "planner")

        # Recall the case rather than restating it.
        case = gov.get_entity("case", case_id, agent_id="planner") or {}
        counterparty_name = case.get("counterparty", "the counterparty")
        task = f"resolve {counterparty_name} exception"

        if use_vertex:
            try:
                task = agent.plan(case_id) or task
            except Exception as exc:  # noqa: BLE001 - a model outage must not kill the demo
                task = f"{task} (planner fallback: {type(exc).__name__})"

        agent.write_assignment(case_id, task)
        return {
            **state,
            "case": case,
            "recalled_from_memory": bool(case),
            "messages": _say(state, f"Atlas assigned {case_id}"),
        }

    def worker_node(state: AgentState) -> AgentState:
        from agents import WorkerAgent

        case_id = state.get("case_id", DEFAULT_CASE_ID)
        agent = WorkerAgent(gov, "worker")
        case = state.get("case") or {}
        policy = gov.get_reference("policy:vendor-payout") or {}
        threshold = policy.get("dual_approval_threshold_usd", 10000)
        amount = case.get("amount_usd", 0)

        # The worker is operational: it honours a recorded pre-approval on the case and
        # otherwise falls back to the policy threshold. The auditor (next node) ignores
        # pre-approval and applies policy strictly. That division of responsibility is
        # what makes a genuine contradiction possible -- and it is exactly the payments
        # failure mode this project exists for, because a poisoned "pre-approved" record
        # is what moves real money.
        preapproved = bool(case.get("preapproved"))
        action = "released" if preapproved or amount <= threshold else "held"
        agent.execute(case_id, action)
        gov.set_entity(
            "journal",
            "payout-worker",
            {
                "status": action,
                "case": case_id,
                "amount_usd": amount,
                "relied_on_preapproval": preapproved,
            },
            agent_id="worker",
            evidence_ref="journal:vesper-action",
        )
        return {
            **state,
            "policy": policy,
            "messages": _say(state, f"Vesper recorded payout {action}"),
        }

    def auditor_node(state: AgentState) -> AgentState:
        from agents import AuditorAgent

        case_id = state.get("case_id", DEFAULT_CASE_ID)
        agent = AuditorAgent(gov, "auditor")
        case = state.get("case") or {}
        amount = case.get("amount_usd", 0)

        audit = agent.audit(amount)
        # The auditor independently records its own view of the payout status. When it
        # disagrees with the worker, that disagreement is what the next node detects.
        gov.set_entity(
            "journal",
            "payout-auditor",
            {
                "status": "held" if audit["requires_dual_approval"] else "released",
                "case": case_id,
                "amount_usd": amount,
            },
            agent_id="auditor",
            evidence_ref="journal:kestrel-audit",
        )
        return {
            **state,
            "audit": audit,
            "messages": _say(state, f"Kestrel audited ${amount:,.0f}"),
        }

    def reconcile_node(state: AgentState) -> AgentState:
        """Detect the contradiction from memory; open a dispute only if one exists."""
        case_id = state.get("case_id", DEFAULT_CASE_ID)
        congress = DisputeCongress(gov)

        worker_view = gov.get_entity("journal", "payout-worker", agent_id="worker")
        auditor_view = gov.get_entity("journal", "payout-auditor", agent_id="auditor")
        contradiction = congress.detect_contradiction(worker_view, auditor_view or {})

        dispute_body: dict[str, Any] | None = None
        if contradiction and worker_view and auditor_view:
            from ledgermind.chain import content_hash

            record = congress.open_dispute(
                dispute_id=f"{case_id}-01",
                subject_category="journal",
                subject_name="payout-status",
                version_a=worker_view,
                version_b=auditor_view,
                agent_a="worker",
                agent_b="auditor",
                hash_a=content_hash(worker_view),
                hash_b=content_hash(auditor_view),
            )
            dispute_body = record.to_body()

        message = (
            "Congress opened dispute on payout status"
            if contradiction
            else "No contradiction detected"
        )
        return {
            **state,
            "contradiction": contradiction,
            "dispute": dispute_body,
            "outcome": "audited",
            "messages": _say(state, message),
        }

    builder = StateGraph(AgentState)
    builder.add_node("planner", planner_node)
    builder.add_node("worker", worker_node)
    builder.add_node("auditor", auditor_node)
    builder.add_node("reconcile", reconcile_node)
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "worker")
    builder.add_edge("worker", "auditor")
    builder.add_edge("auditor", "reconcile")
    builder.add_edge("reconcile", END)
    return builder.compile()
