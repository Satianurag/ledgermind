"""Ungoverned Sibyl probe for ASR baseline arm (real MemoryClient, no governance)."""

from __future__ import annotations

import tempfile

from sibyl_memory_client import MemoryClient


def vanilla_poison_succeeded(prompt: str, *, trust_tier: str) -> bool:
    """True when poison lands in vanilla Sibyl (no Ledgermind governance layer)."""
    db_dir = tempfile.mkdtemp()
    client = MemoryClient.local(f"{db_dir}/vanilla.db")
    client.set_entity("external:inject", "poison", {"text": prompt, "trust_tier": trust_tier})
    hits = client.search_entities(prompt[:32] if prompt else "poison")
    return len(hits) > 0
