"""Chain verification API — re-walk any tree and name the first broken link."""

from __future__ import annotations

from typing import Any

from ledgermind.chain import GENESIS_HASH, ChainVerificationResult, chain_link


def verify_chain(tree: str, entries: list[dict[str, Any]]) -> ChainVerificationResult:
    """Verify a list of chain entries in sequence order."""
    if not entries:
        return ChainVerificationResult(
            ok=True,
            tree=tree,
            entries_checked=0,
            message="empty chain",
        )

    sorted_entries = sorted(entries, key=lambda e: e.get("sequence", 0))
    prev_hash = GENESIS_HASH
    for idx, entry in enumerate(sorted_entries):
        seq = entry.get("sequence", idx)
        stamp = entry.get("stamp", {})
        body = entry.get("body", {})
        expected = chain_link(prev_hash, stamp, body)
        actual = entry.get("hash", "")
        if actual != expected:
            return ChainVerificationResult(
                ok=False,
                tree=tree,
                entries_checked=idx,
                broken_sequence=seq,
                expected_hash=expected,
                actual_hash=actual,
                message=f"broken link at sequence {seq}",
            )
        prev_hash = actual

    return ChainVerificationResult(
        ok=True,
        tree=tree,
        entries_checked=len(sorted_entries),
        message="chain intact",
    )
