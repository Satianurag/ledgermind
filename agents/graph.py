"""LangGraph agent graph wiring (PRD §6.3)."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from ledgermind.store import GovernedMemoryClient


class AgentState(TypedDict, total=False):
    case_id: str
    messages: list[str]
    audit: dict[str, Any]
    outcome: str


def build_demo_graph(gov: GovernedMemoryClient):
    """Three-agent reference topology: planner → worker → auditor."""

    def planner_node(state: AgentState) -> AgentState:
        from agents import PlannerAgent

        agent = PlannerAgent(gov, "planner")
        agent.write_assignment(state.get("case_id", "CASE-2214"), "resolve Meridian exception")
        return {**state, "messages": state.get("messages", []) + ["Atlas assigned case"]}

    def worker_node(state: AgentState) -> AgentState:
        from agents import WorkerAgent

        agent = WorkerAgent(gov, "worker")
        agent.execute(state.get("case_id", "CASE-2214"), "held")
        return {**state, "messages": state.get("messages", []) + ["Vesper recorded action"]}

    def auditor_node(state: AgentState) -> AgentState:
        from agents import AuditorAgent

        agent = AuditorAgent(gov, "auditor")
        audit = agent.audit(12400)
        return {
            **state,
            "audit": audit,
            "outcome": "audited",
            "messages": state.get("messages", []) + ["Kestrel completed audit"],
        }

    builder = StateGraph(AgentState)
    builder.add_node("planner", planner_node)
    builder.add_node("worker", worker_node)
    builder.add_node("auditor", auditor_node)
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "worker")
    builder.add_edge("worker", "auditor")
    builder.add_edge("auditor", END)
    return builder.compile()
