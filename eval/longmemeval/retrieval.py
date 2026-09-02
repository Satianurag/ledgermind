"""Three retrieval gates over one shared Sibyl store.

The store is identical across arms; only the gate differs. That isolates the variable:
we are measuring the gate, not the substrate.

  none                 top-k by relevance. No provenance signal. (vanilla Sibyl)
  provenance_weighted  additive trust penalty on the score. This is the formulation
                       arXiv 2608.21230 shows has "no usable middle ground": small
                       weights do nothing, large weights become categorical exclusion.
  bounded_occupancy    provenance reserves capacity instead of penalising score.
                       Untrusted content may occupy at most `cap` of the k slots, so an
                       attacker cannot outbid trusted content by flooding -- but leftover
                       slots still fall through to untrusted content, so genuine untrusted
                       evidence is never categorically excluded. This is the gate that
                       paper calls for and states it did not implement or evaluate.
"""

from __future__ import annotations

import math
from typing import Any

from ledgermind.provenance import score_source_trust
from sibyl_memory_client import MemoryClient

CATEGORY_PREFIX = "mem"


def ingest(client: MemoryClient, docs: list[dict[str, Any]]) -> None:
    """Write every document into one shared store, trust encoded in the category."""
    for doc in docs:
        client.set_entity(
            f"{CATEGORY_PREFIX}:{doc['trust']}",
            doc["doc_id"],
            {
                "text": doc["text"],
                "question_id": doc["question_id"],
                "is_poison": doc["is_poison"],
                "is_evidence": doc["is_evidence"],
            },
        )


def _trust_of(category: str) -> str:
    return category.split(":", 1)[1] if ":" in category else "unknown"


def _relevance(hits: list[dict[str, Any]]) -> list[float]:
    """Normalise FTS5 rank to [0,1], higher = more relevant.

    bm25 ranks come back negative (more negative = better match), and upstream has an
    open clamp issue, so normalise defensively rather than trusting the sign.
    """
    raw = []
    for hit in hits:
        try:
            value = float(hit.get("rank") or 0.0)
        except (TypeError, ValueError):
            value = 0.0
        raw.append(-value if value < 0 else value)
    if not raw:
        return []
    lo, hi = min(raw), max(raw)
    if math.isclose(hi, lo):
        return [1.0] * len(raw)
    return [(v - lo) / (hi - lo) for v in raw]


# Sibyl sanitises FTS queries and joins terms conjunctively: passing a whole question
# means a document is dropped unless it contains *every* content word, so the evidence
# session is usually never retrieved at all. Operators (OR) are stripped; quoted phrases
# survive. So the pool is built by unioning several short per-term queries and scoring by
# how many of them a document answers. Verified against sibyl-memory-client 0.7.0.
_STOPWORDS = frozenset("""
a an and are as at be been but by did do does for from had has have how i if in is it
its me my of on or our so than that the их their them then there these they this to was
were what when where which who why will with you your about after before during
""".split())


def _terms(question: str, *, limit: int = 8) -> list[str]:
    seen: list[str] = []
    for raw in question.lower().replace("?", " ").replace(",", " ").split():
        word = "".join(ch for ch in raw if ch.isalnum() or ch == "'")
        if len(word) < 3 or word in _STOPWORDS or word in seen:
            continue
        seen.append(word)
        if len(seen) == limit:
            break
    return seen


def build_pool(client: MemoryClient, question: str, *, pool: int = 40) -> list[dict[str, Any]]:
    """Union short per-term searches into one candidate pool, scored by term coverage."""
    merged: dict[str, dict[str, Any]] = {}
    terms = _terms(question)
    for term in terms:
        try:
            hits = client.search(term, limit=pool)
        except Exception:  # noqa: BLE001 - a malformed term must not kill the run
            continue
        for position, hit in enumerate(hits):
            key = hit.get("key") or hit.get("name", "")
            if not key:
                continue
            entry = merged.setdefault(key, {"hit": hit, "coverage": 0, "best": position})
            entry["coverage"] += 1
            entry["best"] = min(entry["best"], position)

    if not merged:
        return client.search(question, limit=pool)

    ordered = sorted(
        merged.values(), key=lambda e: (-e["coverage"], e["best"])
    )
    out = []
    for entry in ordered[:pool]:
        hit = dict(entry["hit"])
        # Coverage is the relevance signal: rank alone is near-constant across the
        # single-term searches that produced this pool.
        hit["rank"] = -float(entry["coverage"])
        out.append(hit)
    return out


def retrieve(
    client: MemoryClient,
    query: str,
    *,
    gate: str = "none",
    k: int = 5,
    pool: int = 40,
    trust_weight: float = 0.15,
    untrusted_cap: float = 0.20,
) -> list[dict[str, Any]]:
    hits = build_pool(client, query, pool=pool)
    if not hits:
        return []

    scores = _relevance(hits)
    items: list[dict[str, Any]] = []
    for hit, score in zip(hits, scores):
        trust = _trust_of(hit.get("category", ""))
        body = hit.get("body")
        if isinstance(body, str):
            import json

            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                body = {"text": body}
        items.append({
            "doc_id": hit.get("key") or hit.get("name", ""),
            "text": (body or {}).get("text", ""),
            "question_id": (body or {}).get("question_id", ""),
            "is_poison": bool((body or {}).get("is_poison")),
            "is_evidence": bool((body or {}).get("is_evidence")),
            "trust": trust,
            "trust_score": score_source_trust(trust),
            "relevance": score,
        })

    if gate == "none":
        return items[:k]

    if gate == "provenance_weighted":
        for item in items:
            item["gated_score"] = item["relevance"] - trust_weight * (1.0 - item["trust_score"])
        return sorted(items, key=lambda i: i["gated_score"], reverse=True)[:k]

    if gate == "bounded_occupancy":
        # Occupancy, not score. Untrusted content gets at least one slot and at most
        # `budget`, whatever its relevance. At least one, so genuine untrusted evidence is
        # never categorically excluded (the Corpus N failure of hard filtering). At most
        # `budget`, so an attacker cannot take the context by flooding it with highly
        # relevant poison. Unused trusted capacity is left empty rather than backfilled
        # with untrusted content -- backfilling would hand the flood the slots back.
        budget = max(1, int(math.floor(k * untrusted_cap)))
        trusted = [i for i in items if i["trust_score"] >= 0.6]
        untrusted = [i for i in items if i["trust_score"] < 0.6]
        selected = trusted[: k - budget] + untrusted[:budget]
        return sorted(selected, key=lambda i: i["relevance"], reverse=True)[:k]

    raise ValueError(f"unknown gate: {gate}")


def ingest_capped(
    client: MemoryClient,
    docs: list[dict[str, Any]],
    *,
    max_pct: float = 0.85,
) -> int:
    """Ingest until the store approaches Sibyl's hard free-tier cap.

    Returns the number of documents written. Callers must treat a short write as a
    shard boundary, not as a partial corpus: a corpus missing evidence sessions would
    silently understate accuracy for every arm.
    """
    written = 0
    for index, doc in enumerate(docs):
        try:
            client.set_entity(
                f"{CATEGORY_PREFIX}:{doc['trust']}",
                doc["doc_id"],
                {
                    "text": doc["text"],
                    "question_id": doc["question_id"],
                    "is_poison": doc["is_poison"],
                    "is_evidence": doc["is_evidence"],
                },
            )
        except Exception:  # noqa: BLE001 - CapExceededError and friends
            return written
        written += 1
        if index % 25 == 0:
            try:
                if client.free_tier_status().get("pct_used", 0.0) >= max_pct:
                    return written
            except Exception:  # noqa: BLE001
                pass
    return written


def store_pct_used(client: MemoryClient) -> float:
    try:
        return float(client.free_tier_status().get("pct_used", 0.0))
    except Exception:  # noqa: BLE001
        return 0.0
