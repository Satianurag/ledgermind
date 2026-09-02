"""Fresh-session recall beat (FR-8) — cold start decision flip."""

from __future__ import annotations

import subprocess
import sys

from ledgermind.chain import content_hash
from ledgermind.config import get_settings
from ledgermind.decisions import build_decision_context, select_vendor
from ledgermind.store import GovernedMemoryClient


def recall_and_decide() -> dict:
    settings = get_settings()
    with GovernedMemoryClient(settings.sibyl_memory_db) as gov:
        priority = gov.get_state("priorities")
        counterparty = gov.get_entity("counterparty", "meridian-components-ltd", agent_id="worker")
        events = gov.read_events(limit=5)
        search_hits = gov.search_entities("Meridian")
        context = build_decision_context(gov)
        decision = select_vendor(context)
        return {
            "priority": priority,
            "counterparty": counterparty,
            "counterparty_hash": content_hash(counterparty) if counterparty else None,
            "events_count": len(events),
            "search_hits": len(search_hits),
            "decision": decision,
            "commit": _git_short_hash(),
        }


def _git_short_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def main() -> int:
    result = recall_and_decide()
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
