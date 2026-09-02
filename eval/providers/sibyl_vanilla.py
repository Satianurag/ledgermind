"""Promptfoo provider: vanilla Sibyl (no governance)."""

import json

from eval.vanilla_probe import vanilla_poison_succeeded


def call_api(prompt, options, context):
    trust = context["vars"].get("trust_tier", "unknown")
    poisoned = vanilla_poison_succeeded(prompt, trust_tier=trust)
    return {"output": json.dumps({"poison_succeeded": poisoned, "governed": False})}
