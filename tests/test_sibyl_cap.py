"""Sibyl cap behavior tests (PRD §6.13 S2/S3)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from sibyl_memory_client import MemoryClient


def test_demo_db_under_2mb_budget():
    """Design target: demo dataset stays under 2 MiB."""
    tmp = tempfile.mkdtemp()
    db = Path(tmp) / "cap.db"
    client = MemoryClient.local(str(db))
    for i in range(100):
        client.set_entity("test:cap", f"item-{i}", {"data": "x" * 100})
    size = db.stat().st_size
    assert size < 2 * 1024 * 1024, f"DB size {size} exceeds 2 MiB design budget"
