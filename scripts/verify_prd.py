"""PRD compliance verification script — run before submission."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ("Tests pass", ["uv", "run", "pytest", "tests/", "-q", "--ignore=tests/test_vertex_live.py"]),
    ("ASR eval", ["uv", "run", "python", "eval/run_asr.py"]),
    ("Gauntlet gate", ["uv", "run", "pytest", "tests/test_gauntlet.py", "-q"]),
    ("MCP parity", ["uv", "run", "python", "scripts/exercise_mcp.py"]),
    ("Deletion test", ["uv", "run", "pytest", "tests/test_deletion.py", "-q"]),
    ("Scope guard", ["uv", "run", "pytest", "tests/test_prd_scope.py", "-q"]),
    ("Ruff lint", ["uv", "run", "ruff", "check", "packages/python", "tests", "demo", "agents", "onchain", "ui"]),
]


def main() -> int:
    failed = []
    for name, cmd in CHECKS:
        print(f"Checking: {name}...")
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  FAIL: {r.stderr[:300] or r.stdout[:300]}")
            failed.append(name)
        else:
            print("  OK")
    if failed:
        print(f"\nFailed checks: {failed}")
        return 1
    print("\nPRD compliance checks passed (Vertex smoke requires live GCP IAM).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
