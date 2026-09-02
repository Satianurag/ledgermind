"""LangGraph reference deployment wiring."""

from __future__ import annotations

import tempfile
from pathlib import Path

from ledgermind.store import GovernedMemoryClient

from agents.graph import build_demo_graph


def test_demo_graph_runs_three_agents():
    tmp = tempfile.mkdtemp()
    with GovernedMemoryClient(Path(tmp) / "graph.db") as gov:
        graph = build_demo_graph(gov)
        result = graph.invoke({"case_id": "CASE-2214", "messages": []})
    assert result["outcome"] == "audited"
    assert len(result["messages"]) == 3
