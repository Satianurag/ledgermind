"""MCP tool parity — exercise all 8 sibyl-memory-mcp tools via governed writes."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from ledgermind.store import GovernedMemoryClient

# Official MCP tool names (sibyl-memory-mcp 0.1.14)
MCP_TOOLS = (
    "memory_remember",
    "memory_recall",
    "memory_search",
    "memory_list",
    "memory_forget",
    "memory_set_state",
    "memory_get_state",
    "memory_record_event",
)


def exercise_all_tools(db_path: str | None = None) -> dict[str, Any]:
    """Run each MCP tool once through GovernedMemoryClient (SDK/MCP parity)."""
    path = db_path or str(Path(tempfile.mkdtemp()) / "mcp-parity.db")
    results: dict[str, Any] = {"db": path, "tools": {}}

    with GovernedMemoryClient(path) as gov:
        gov.set_state("mcp:session", {"phase": "start"}, agent_id="mcp", evidence_ref="mcp:set_state")
        state = gov.get_state("mcp:session")
        results["tools"]["memory_set_state"] = {"ok": state is not None}
        results["tools"]["memory_get_state"] = {"ok": state == {"phase": "start"}}

        gov.set_entity(
            "mcp:demo",
            "item-1",
            {"text": "parity-check"},
            agent_id="mcp",
            evidence_ref="mcp:remember",
        )
        recalled = gov.get_entity("mcp:demo", "item-1", agent_id="mcp")
        results["tools"]["memory_remember"] = {"ok": recalled is not None}
        results["tools"]["memory_recall"] = {"ok": recalled == {"text": "parity-check"}}

        hits = gov.search_entities("parity")
        results["tools"]["memory_search"] = {"ok": len(hits) >= 1}

        listed = gov.raw.list_entities()
        results["tools"]["memory_list"] = {"ok": len(listed) >= 1}

        gov.write_event(agent_id="mcp", acted={"tool": "memory_record_event"}, evidence_ref="mcp:event")
        results["tools"]["memory_record_event"] = {"ok": True}

        gov.archive_entity("mcp:demo", "item-1", agent_id="mcp")
        hits_after_forget = gov.search_entities("parity")
        results["tools"]["memory_forget"] = {"ok": len(hits_after_forget) == 0}

    results["ok"] = all(t.get("ok") for t in results["tools"].values())
    results["tools_exercised"] = list(results["tools"].keys())
    return results
