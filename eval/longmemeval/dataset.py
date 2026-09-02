"""LongMemEval oracle dataset: fetch, cache, and take a deterministic subset.

Oracle setting = the model is given only the evidence sessions. It is the upper-bound
retrieval condition, which is what we want: any accuracy we lose under poisoning is
attributable to the poison and the gate, not to a weak retriever.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

_BASE_URL = "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main"
SPLITS = {
    # Evidence sessions only. Upper-bound retrieval, but ~1.5 sessions per question, so
    # one poison per question lands at ~40% contamination -- far above any realistic
    # threat model.
    "oracle": "longmemeval_oracle.json",
    # Full haystack with distractor sessions. This is the split that supports a realistic
    # contamination rate (the ~1.2% used in arXiv 2608.21230).
    "s": "longmemeval_s_cleaned.json",
}
ORACLE_URL = f"{_BASE_URL}/{SPLITS['oracle']}"
# demo-data/ is gitignored: a 15 MB dataset does not belong in the repo.
CACHE_DIR = Path(__file__).resolve().parents[2] / "demo-data" / "longmemeval"
CACHE_FILE = CACHE_DIR / "longmemeval_oracle.json"


def fetch_split(split: str = "oracle") -> Path:
    """Download a split once and cache it under gitignored demo-data/."""
    if split not in SPLITS:
        raise ValueError(f"unknown split {split!r}; expected one of {sorted(SPLITS)}")
    target = CACHE_DIR / ("longmemeval_oracle.json" if split == "oracle" else "longmemeval_s.json")
    if target.exists() and target.stat().st_size > 1_000_000:
        return target
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    url = os.environ.get("LONGMEMEVAL_URL", f"{_BASE_URL}/{SPLITS[split]}")
    tmp = target.with_suffix(".part")
    urllib.request.urlretrieve(url, tmp)  # noqa: S310 - pinned HTTPS dataset host
    tmp.rename(target)
    return target


def fetch_oracle() -> Path:
    return fetch_split("oracle")


def load_split(split: str = "oracle") -> list[dict[str, Any]]:
    return json.loads(fetch_split(split).read_text())


def load_oracle() -> list[dict[str, Any]]:
    return load_split("oracle")


def _stable_key(record: dict[str, Any]) -> str:
    """Deterministic ordering independent of file order, so subsets are reproducible."""
    return hashlib.sha256(record["question_id"].encode()).hexdigest()


def subset(records: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    """Deterministic n-record subset, stratified across question types.

    Stratifying matters: `knowledge-update` questions are the ones where a later fact
    supersedes an earlier one, which is exactly the case poisoning exploits. A random
    subset can under-sample them and flatter every arm.
    """
    if n <= 0 or n >= len(records):
        return sorted(records, key=_stable_key)

    by_type: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_type.setdefault(record.get("question_type", "unknown"), []).append(record)
    for bucket in by_type.values():
        bucket.sort(key=_stable_key)

    picked: list[dict[str, Any]] = []
    types = sorted(by_type)
    index = 0
    while len(picked) < n:
        progressed = False
        for qtype in types:
            bucket = by_type[qtype]
            if index < len(bucket):
                picked.append(bucket[index])
                progressed = True
                if len(picked) == n:
                    break
        if not progressed:
            break
        index += 1
    return sorted(picked, key=_stable_key)


def session_text(session: list[dict[str, Any]], *, max_bytes: int | None = None) -> str:
    """Flatten one chat session into the text actually stored in memory.

    `max_bytes` matters because of a measured Sibyl property: stored size is ~5.6x the
    raw text once the FTS5 index and search shadow are counted, so the 5 MiB free-tier
    cap holds only ~0.94 MB of text. Truncating sessions is what makes a realistic
    contamination rate reachable at all -- see docs/eval-methodology.md.
    """
    text = "\n".join(
        f"{turn.get('role', 'user')}: {turn.get('content', '')}" for turn in session
    ).strip()
    if max_bytes is None:
        return text
    raw = text.encode("utf-8")
    if len(raw) <= max_bytes:
        return text
    return raw[:max_bytes].decode("utf-8", errors="ignore")


def shard(records: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    """Split records into cap-sized shards.

    Sibyl's free tier is a hard 5 MiB per store, so a corpus large enough to give a
    realistic contamination rate does not fit in one database. Each shard is its own
    store; results are pooled across shards. Shards are disjoint, so pooling is a plain
    concatenation of independent runs.
    """
    if size <= 0:
        return [records]
    return [records[i : i + size] for i in range(0, len(records), size)]
