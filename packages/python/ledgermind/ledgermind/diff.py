"""Memory snapshot diff for montage + CLI (PRD §6.9)."""

from __future__ import annotations

import difflib
import json
from typing import Any

from ledgermind.chain import content_hash


def snapshot_entities(entities: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for ent in entities:
        key = f"{ent.get('category')}:{ent.get('name')}"
        body = ent.get("body", {})
        out[key] = {
            "body": body,
            "hash": content_hash(body) if isinstance(body, dict) else str(body),
            "tier": ent.get("category", "").split(":")[0] if ":" in ent.get("category", "") else "warm",
        }
    return out


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_keys = set(before)
    after_keys = set(after)
    added = sorted(after_keys - before_keys)
    removed = sorted(before_keys - after_keys)
    mutated = []
    for key in sorted(before_keys & after_keys):
        if before[key]["hash"] != after[key]["hash"]:
            mutated.append(
                {
                    "key": key,
                    "old_hash": before[key]["hash"],
                    "new_hash": after[key]["hash"],
                    "unified_diff": "\n".join(
                        difflib.unified_diff(
                            json.dumps(before[key]["body"], indent=2, sort_keys=True).splitlines(),
                            json.dumps(after[key]["body"], indent=2, sort_keys=True).splitlines(),
                            fromfile="before",
                            tofile="after",
                            lineterm="",
                        )
                    ),
                }
            )
    return {"added": added, "removed": removed, "mutated": mutated}


def render_rich_table(diff: dict[str, Any]) -> str:
    lines = ["Memory diff (git log for the mind)", "=" * 40]
    for label, keys in [("ADDED", diff["added"]), ("REMOVED", diff["removed"])]:
        if keys:
            lines.append(f"\n{label}:")
            for k in keys:
                lines.append(f"  + {k}")
    if diff["mutated"]:
        lines.append("\nMUTATED:")
        for m in diff["mutated"]:
            lines.append(f"  ~ {m['key']} ({m['old_hash'][:12]} → {m['new_hash'][:12]})")
    return "\n".join(lines)
