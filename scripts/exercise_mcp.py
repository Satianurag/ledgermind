"""Exercise all 8 Sibyl MCP tools once for harness parity (FR-7 AC)."""

from __future__ import annotations

import json
import sys

from ledgermind.mcp_parity import MCP_TOOLS, exercise_all_tools


def main() -> int:
    report = exercise_all_tools()
    print(json.dumps(report, indent=2))
    missing = [name for name in MCP_TOOLS if name not in report.get("tools", {})]
    if missing:
        print(f"Missing tools: {missing}", file=sys.stderr)
        return 1
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
