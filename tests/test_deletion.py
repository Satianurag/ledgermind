"""Deletion test gate — README points here (PRD §1 / rules §03)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agents import PlannerAgent


def test_agents_fail_without_sibyl():
    """Removing Sibyl Memory calls must break agent coordination."""
    mock_gov = MagicMock()
    mock_gov.set_state.side_effect = RuntimeError("Sibyl unavailable")
    agent = PlannerAgent(mock_gov, "planner")
    with pytest.raises(RuntimeError, match="Sibyl unavailable"):
        agent.write_assignment("CASE-2214", "task")
