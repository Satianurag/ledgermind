"""MCP 8-tool parity harness (FR-7)."""

from __future__ import annotations

from ledgermind.mcp_parity import MCP_TOOLS, exercise_all_tools


def test_all_mcp_tools_exercised():
    report = exercise_all_tools()
    assert report["ok"]
    assert set(report["tools"].keys()) == set(MCP_TOOLS)
