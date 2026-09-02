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

ORACLE_URL = (
    "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/"
    "resolve/main/longmemeval_oracle.json"
)
# demo-data/ is gitignored: a 15 MB dataset does not belong in the repo.
CACHE_DIR = Path(__file__).resolve().parents[2] / "demo-data" / "longmemeval"
CACHE_FILE = CACHE_DIR / "longmemeval_oracle.json"


def fetch_oracle() -> Path:
    """Download the oracle split once and cache it locally."""
    if CACHE_FILE.exists() and CACHE_FILE.stat().st_size > 1_000_000:
        return CACHE_FILE
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    url = os.environ.get("LONGMEMEVAL_URL", ORACLE_URL)
    tmp = CACHE_FILE.with_suffix(".part")
    urllib.request.urlretrieve(url, tmp)  # noqa: S310 - pinned HTTPS dataset host
    tmp.rename(CACHE_FILE)
    return CACHE_FILE


def load_oracle() -> list[dict[str, Any]]:
    return json.loads(fetch_oracle().read_text())


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


def session_text(session: list[dict[str, Any]]) -> str:
    """Flatten one chat session into the text actually stored in memory."""
    return "\n".join(
        f"{turn.get('role', 'user')}: {turn.get('content', '')}" for turn in session
    ).strip()
