"""SHA-256 receipt chain with RFC 8785 JCS canonicalization."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import jcs

GENESIS_HASH = "0" * 64


def canonicalize(payload: dict[str, Any] | list[Any]) -> bytes:
    return jcs.canonicalize(payload)


def chain_link(prev_hash: str, stamp: dict[str, Any], body: dict[str, Any] | list[Any]) -> str:
    envelope = {"stamp": stamp, "body": body}
    digest_input = prev_hash.encode("utf-8") + canonicalize(envelope)
    return hashlib.sha256(digest_input).hexdigest()


def content_hash(body: dict[str, Any] | list[Any]) -> str:
    return hashlib.sha256(canonicalize(body)).hexdigest()


@dataclass
class ChainEntry:
    tree: str
    sequence: int
    prev_hash: str
    hash: str
    stamp: dict[str, Any]
    body: dict[str, Any] | list[Any]

    def to_record(self) -> dict[str, Any]:
        return {
            "tree": self.tree,
            "sequence": self.sequence,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
            "stamp": self.stamp,
            "body": self.body,
        }


@dataclass
class ChainVerificationResult:
    ok: bool
    tree: str
    entries_checked: int
    broken_sequence: int | None = None
    expected_hash: str | None = None
    actual_hash: str | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "tree": self.tree,
            "entries_checked": self.entries_checked,
            "broken_sequence": self.broken_sequence,
            "expected_hash": self.expected_hash,
            "actual_hash": self.actual_hash,
            "message": self.message,
        }
