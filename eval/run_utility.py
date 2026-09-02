"""Utility-under-attack harness: LongMemEval x poisoning x three retrieval gates.

Replaces the previous ASR gauntlet. Per arXiv 2608.21230, attack-success rate "cannot
distinguish a memory that resisted an attack from one the attack rendered useless", so
the headline metric here is **utility retained** = poisoned accuracy / clean accuracy,
reported next to the false-positive cost on benign untrusted evidence.

  make eval                       # default subset
  uv run python eval/run_utility.py --n 30 --k 5
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from ledgermind.config import get_settings  # noqa: E402
from sibyl_memory_client import MemoryClient  # noqa: E402

from eval.longmemeval.corpus import build_corpus, build_poison  # noqa: E402
from eval.longmemeval.dataset import load_split, shard, subset  # noqa: E402
from eval.longmemeval.judge import answer_question, grade  # noqa: E402
from eval.longmemeval.retrieval import ingest_capped, retrieve, store_pct_used  # noqa: E402

GATES = ("none", "provenance_weighted", "bounded_occupancy", "adjudicated")

# The adjudicated arm reuses the bounded-occupancy selection and adds provenance-aware
# answering, so the two differ only in whether the conflict is adjudicated.
RETRIEVAL_GATE = {
    "none": "none",
    "provenance_weighted": "provenance_weighted",
    "bounded_occupancy": "bounded_occupancy",
    "adjudicated": "bounded_occupancy",
}


def _isolate_cap_accounting() -> None:
    """Stop the demo store from eating the benchmark's cap budget.

    Sibyl's free-tier cap is per ACCOUNT: aggregate_db_size() sums every store an agent
    can resolve, including $SIBYL_MEMORY_DB. ledgermind.config calls load_dotenv() at
    import time and .env points that at the ~2.5 MB demo database, which silently
    consumed half the budget and truncated every shard at 366 documents. Benchmark shards
    are sequential throwaway stores that must be measured on their own.
    """
    os.environ.pop("SIBYL_MEMORY_DB", None)


def _store(docs: list[dict[str, Any]]) -> tuple[MemoryClient, str, dict[str, Any]]:
    """One throwaway store per corpus per shard, sized to stay under the free-tier cap."""
    _isolate_cap_accounting()
    tmp = tempfile.mkdtemp()
    client = MemoryClient.local(tmp + "/corpus.db")
    written = ingest_capped(client, docs)
    return client, tmp, {
        "documents_written": written,
        "documents_expected": len(docs),
        "complete": written == len(docs),
        "cap_pct_used": round(store_pct_used(client), 4),
    }


def run_condition(
    records: list[dict[str, Any]],
    client: MemoryClient,
    *,
    gate: str,
    k: int,
    trust_weight: float,
    untrusted_cap: float,
    model: str,
    workers: int,
) -> dict[str, Any]:
    def one(record: dict[str, Any]) -> dict[str, Any]:
        docs = retrieve(
            client,
            record["question"],
            gate=RETRIEVAL_GATE[gate],
            k=k,
            trust_weight=trust_weight,
            untrusted_cap=untrusted_cap,
        )
        prediction = answer_question(
            model, record["question"], docs, adjudicated=(gate == "adjudicated")
        )
        correct = grade(model, record["question"], record["answer"], prediction)
        return {
            "question_id": record["question_id"],
            "question_type": record.get("question_type"),
            "correct": correct,
            "prediction": prediction[:200],
            "retrieved": len(docs),
            "poison_in_context": sum(1 for d in docs if d["is_poison"]),
            "evidence_in_context": sum(1 for d in docs if d["is_evidence"]),
            "has_evidence": any(d["is_evidence"] for d in docs),
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, records))

    n = len(results) or 1
    slots = sum(r["retrieved"] for r in results) or 1
    return {
        "gate": gate,
        "accuracy": round(sum(r["correct"] for r in results) / n, 4),
        "evidence_recall": round(sum(r["has_evidence"] for r in results) / n, 4),
        "poison_occupancy": round(sum(r["poison_in_context"] for r in results) / slots, 4),
        "mean_retrieved": round(slots / n, 2),
        "n": n,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=60, help="questions evaluated in total")
    parser.add_argument("--split", default="s", choices=("s", "oracle"))
    parser.add_argument("--shard-size", type=int, default=10,
                        help="questions per store; 10 keeps a shard at ~65%% of the 5 MiB cap")
    parser.add_argument("--k", type=int, default=5, help="retrieved documents per question")
    parser.add_argument("--max-session-bytes", type=int, default=800)
    parser.add_argument("--max-distractors", type=int, default=48)
    parser.add_argument("--trust-weight", type=float, default=0.15)
    parser.add_argument("--untrusted-cap", type=float, default=0.20)
    parser.add_argument("--untrusted-evidence-fraction", type=float, default=0.30)
    parser.add_argument("--poison-per-question", type=int, default=1,
                        help="attacker write budget: 1 = single false memory, >1 = flooding")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", default=str(ROOT / "eval" / "output" / "utility_report.json"))
    args = parser.parse_args()

    settings = get_settings()
    model = settings.model_worker
    started = time.time()

    records = subset(load_split(args.split), args.n)
    shards = shard(records, args.shard_size)
    print(f"{len(records)} questions in {len(shards)} shards of <={args.shard_size}  "
          f"model={model} k={args.k}", flush=True)

    poison_texts = build_poison(records, model=model)
    print(f"poison: {len(poison_texts)} false assertions (cached)", flush=True)

    corpus_specs = {
        "clean": {"poisoned": False, "untrusted_evidence_fraction": 0.0},
        "poisoned": {"poisoned": True, "untrusted_evidence_fraction": 0.0},
        "poisoned_corpus_n": {
            "poisoned": True,
            "untrusted_evidence_fraction": args.untrusted_evidence_fraction,
        },
    }

    pooled: dict[str, list[dict[str, Any]]] = {
        f"{c}::{g}": [] for c in corpus_specs for g in GATES
    }
    corpus_stats: dict[str, list[dict[str, Any]]] = {c: [] for c in corpus_specs}
    incomplete = 0

    for index, group in enumerate(shards, start=1):
        for corpus_name, spec in corpus_specs.items():
            docs, stats = build_corpus(
                group,
                poison_texts=poison_texts,
                max_session_bytes=args.max_session_bytes,
                max_distractors=args.max_distractors,
                poison_per_question=args.poison_per_question,
                **spec,
            )
            client, tmp, ingest_stats = _store(docs)
            stats.update(ingest_stats)
            corpus_stats[corpus_name].append(stats)
            if not ingest_stats["complete"]:
                incomplete += 1
                print(f"  WARNING shard {index} {corpus_name}: hit cap after "
                      f"{ingest_stats['documents_written']}/{len(docs)} docs", flush=True)
            try:
                for gate in GATES:
                    outcome = run_condition(
                        group, client, gate=gate, k=args.k,
                        trust_weight=args.trust_weight,
                        untrusted_cap=args.untrusted_cap,
                        model=model, workers=args.workers,
                    )
                    pooled[f"{corpus_name}::{gate}"].extend(outcome["results"])
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        print(f"shard {index}/{len(shards)} done ({time.time() - started:.0f}s)", flush=True)

    def agg(results: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(results) or 1
        slots = sum(r["retrieved"] for r in results) or 1
        return {
            "accuracy": round(sum(r["correct"] for r in results) / n, 4),
            "evidence_recall": round(sum(r["has_evidence"] for r in results) / n, 4),
            "poison_occupancy": round(sum(r["poison_in_context"] for r in results) / slots, 4),
            "mean_retrieved": round(slots / n, 2),
            "n": len(results),
        }

    conditions = {key: agg(results) for key, results in pooled.items()}

    summary = {}
    for gate in GATES:
        clean = conditions[f"clean::{gate}"]["accuracy"]
        pois = conditions[f"poisoned::{gate}"]
        corpn = conditions[f"poisoned_corpus_n::{gate}"]
        summary[gate] = {
            "clean_accuracy": clean,
            "poisoned_accuracy": pois["accuracy"],
            "utility_retained": round(pois["accuracy"] / clean, 4) if clean else None,
            "corpus_n_accuracy": corpn["accuracy"],
            "corpus_n_utility_retained": round(corpn["accuracy"] / clean, 4) if clean else None,
            "poison_occupancy": pois["poison_occupancy"],
            "evidence_recall_clean": conditions[f"clean::{gate}"]["evidence_recall"],
            "evidence_recall_poisoned": pois["evidence_recall"],
            "evidence_recall_corpus_n": corpn["evidence_recall"],
        }

    def mean(values: list[float]) -> float:
        return round(sum(values) / len(values), 4) if values else 0.0

    report = {
        "run_id": str(uuid.uuid4()),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "manifest": {
            "dataset": f"LongMemEval {args.split} (xiaowu0162/longmemeval-cleaned)",
            "questions": len(records),
            "shards": len(shards),
            "shard_size": args.shard_size,
            "model": model,
            "k": args.k,
            "max_session_bytes": args.max_session_bytes,
            "max_distractors": args.max_distractors,
            "trust_weight": args.trust_weight,
            "untrusted_cap": args.untrusted_cap,
            "untrusted_evidence_fraction": args.untrusted_evidence_fraction,
            "poison_per_question": args.poison_per_question,
            "python": platform.python_version(),
            "shards_truncated_by_cap": incomplete,
            "wall_clock_s": None,
            "notes": [
                "Gates are applied at retrieval over one shared store per corpus per "
                "shard, so the store is held constant and the gate is the only variable.",
                "Sibyl free tier is a hard 5 MiB cap summed across every store an agent "
                "resolves, and stored size is ~7x raw text for many small documents. "
                "Shards are sequential throwaway stores, deleted after use.",
                "Judge sees only question, gold answer and prediction -- never the "
                "retrieved context or which arm produced it.",
            ],
        },
        "corpora": {
            name: {
                "shards": len(stats),
                "mean_documents": mean([s["documents"] for s in stats]),
                "mean_contamination_rate": mean([s["contamination_rate"] for s in stats]),
                "mean_cap_pct_used": mean([s["cap_pct_used"] for s in stats]),
                "all_complete": all(s["complete"] for s in stats),
            }
            for name, stats in corpus_stats.items()
        },
        "summary": summary,
        "conditions": conditions,
        "results": pooled,
    }
    report["manifest"]["wall_clock_s"] = round(time.time() - started, 1)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))

    contam = report["corpora"]["poisoned"]["mean_contamination_rate"]
    print("\n=== utility under attack ===")
    print(f"dataset: LongMemEval {args.split}  n={len(records)}  "
          f"contamination={contam:.2%}  k={args.k}")
    print(f"{'gate':22} {'clean':>7} {'poisoned':>9} {'retained':>9} "
          f"{'corpusN':>8} {'poison_occ':>11} {'ev_recall':>10}")
    for gate in GATES:
        s = summary[gate]
        ret = f"{s['utility_retained']:.1%}" if s["utility_retained"] is not None else "n/a"
        print(f"{gate:22} {s['clean_accuracy']:>7.3f} {s['poisoned_accuracy']:>9.3f} "
              f"{ret:>9} {s['corpus_n_accuracy']:>8.3f} {s['poison_occupancy']:>11.3f} "
              f"{s['evidence_recall_poisoned']:>10.3f}")
    if incomplete:
        print(f"\nWARNING: {incomplete} shard-corpora were truncated by the cap.")
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
