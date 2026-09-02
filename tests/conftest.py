"""Pytest fixtures — no fake onchain receipts in demo paths."""

from __future__ import annotations

import pytest
from ledgermind.store import GovernedMemoryClient


@pytest.fixture
def gov(tmp_path):
    db = tmp_path / "test.db"
    with GovernedMemoryClient(str(db)) as client:
        yield client
