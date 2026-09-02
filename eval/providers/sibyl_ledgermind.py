"""Promptfoo provider: Sibyl + Ledgermind governance."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "packages", "python"))

from ledgermind.defense import evaluate_injection
from ledgermind.store import GovernedMemoryClient


def call_api(prompt, options, context):
    trust = context["vars"].get("trust_tier", "unknown")
    db = os.path.join(tempfile.mkdtemp(), "governed.db")
    with GovernedMemoryClient(db) as gov:
        verdict = evaluate_injection(
            gov,
            agent_id="external",
            kind="inject",
            name="poison",
            body={"text": prompt},
            source_trust_tier=trust,
            evidence_ref="gauntlet",
        )
    poison_succeeded = not verdict.caught
    return {"output": json.dumps({"poison_succeeded": poison_succeeded, "governed": True, "paths": verdict.paths_fired})}
