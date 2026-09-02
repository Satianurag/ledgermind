"""PRD scope guard — automated compliance checks."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_IMPORTS = [
    "crewai",
    "openai",
    "anthropic",
    "sibyl_memory_langgraph",
]
FORBIDDEN_PATTERNS = [
    "delete_entity(",
]


def _py_files():
    for pattern in ("packages/python/**/*.py", "agents/**/*.py", "demo/**/*.py", "onchain/**/*.py", "ui/**/*.py"):
        yield from ROOT.glob(pattern)


@pytest.mark.parametrize("forbidden", FORBIDDEN_IMPORTS)
def test_no_forbidden_imports(forbidden: str):
    for path in _py_files():
        text = path.read_text()
        assert f"import {forbidden}" not in text and f"from {forbidden}" not in text, (
            f"{path} uses forbidden {forbidden}"
        )


def test_no_delete_entity_in_demo_path():
  """PRD: delete_entity never used in demo path."""
  for path in _py_files():
    if "test_" in path.name:
      continue
    text = path.read_text()
    assert "delete_entity" not in text, f"{path} calls delete_entity"
