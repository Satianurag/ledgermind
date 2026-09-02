# Evaluation methodology

## Why not attack-success rate

The previous harness reported an ASR of 41% → 10%. Both numbers were wrong, and the way
they were wrong is worth recording.

The "vanilla" arm wrote a string into Sibyl and then searched for that same string,
counting a hit as "the poison succeeded". It measured the SQLite FTS5 tokenizer, not an
attack. The governed arm divided by all 22 gauntlet cases including 6 clean controls; on
attacks only its ASR was 2/16 = 12.5%, which fails the project's own ≤10% target. The
content detector was a regex assembled from the gauntlet's own strings, and 16 of the 22
outcomes were decided by the `trust_tier` label the fixture handed the system.

Beyond the implementation, ASR is the wrong metric. From
[arXiv 2608.21230](https://arxiv.org/abs/2608.21230): ASR "cannot distinguish a memory
that resisted an attack from one the attack rendered useless." A defense that quarantines
everything scores a perfect ASR and destroys the product.

## What we measure instead

**Utility retained** = poisoned accuracy ÷ clean accuracy, on
[LongMemEval](https://github.com/xiaowu0162/LongMemEval) — the benchmark Sibyl itself
reports against (#2 on Oracle, 95.6%). Reported alongside:

- **poison occupancy** — the share of retrieved context the attacker controls
- **evidence recall** — whether the genuine answer was retrieved at all
- **Corpus N accuracy** — accuracy when a fraction of *genuine* evidence is itself marked
  untrusted. This is the fairness test. Without it, any provenance defense looks perfect
  by excluding all untrusted content; Corpus N is where hard filtering destroys the answer
  along with the attack.
- **API error rate** — reported explicitly and excluded from accuracy (see *Throttling*).

## Arms

All four arms read from an identical store. Only the gate differs, so the gate is the
only variable.

| arm | behaviour |
|---|---|
| `none` | top-k by relevance, no provenance signal |
| `provenance_weighted` | additive trust penalty on the score — the formulation arXiv 2608.21230 shows has no usable middle ground |
| `bounded_occupancy` | provenance reserves *capacity*: untrusted content gets at least one and at most `floor(k·cap)` slots |
| `adjudicated` | bounded occupancy + provenance-labelled context, with an explicit rule that a chain-verified internal record beats a contradicting external one |

`bounded_occupancy` is our implementation of the gate arXiv 2608.21230 proposes and
explicitly states it did not build: *"provenance belongs in retrieval as a bounded
occupancy constraint… we have not implemented or evaluated such a gate."*

## Threat model

Taken from the same paper. The adversary can write to memory through an untrusted channel
and knows the likely questions. It cannot elevate its own trust tier, does not optimise
against retrieval feedback, and uses no instruction payload — the poison is a plainly
worded false assertion in ordinary conversation, with no override, role-play or urgency.
This is a weak adversary by design; results are therefore a lower bound on attack
capability and an upper bound on defense effectiveness.

`--poison-per-question` is the attacker's write budget. At 1 it is a single false
assertion; above 1 it is the flooding case, where the same false memory is restated
repeatedly — something any actor with write access can do.

## Measured Sibyl constraints

These shaped the design and are worth knowing independently of this project. All verified
against `sibyl-memory-client` 0.7.0 on 2026-09-02.

1. **The free-tier cap is 5 MiB, not 2 MB.** The docs tiers page states 2 MB;
   `_capcheck.FREE_TIER_CAP_BYTES` is `5 * 1024 * 1024`, raised from 2 MiB on 2026-08-06
   to absorb the v0.5.0 search shadow. Exceeding it raises `CapExceededError` on write.
   There is no free activation path — `PAID_TIERS` is `{sync, team, lifetime, stake,
   enterprise}`.

2. **The cap is per account, not per database.** `aggregate_db_size()` sums every store an
   agent can resolve: the primary DB, `~/.sibyl-memory/memory.db`, Hermes profiles, and
   `$SIBYL_MEMORY_DB`. Because `ledgermind.config` calls `load_dotenv()` at import and
   `.env` points `SIBYL_MEMORY_DB` at the demo store, benchmark shards were silently
   truncated at 366 documents until the harness isolated that variable.

3. **Stored size is ~5.6× raw text for large documents and ~7× for many small ones**
   (FTS5 index plus the folded-trigram search shadow). The 5 MiB cap therefore holds under
   1 MB of text. This is why the corpus is built as sequential 8–10 question shards, each
   its own throwaway store, pooled after the fact.

4. **`search()` is conjunctive with a relax-on-empty fallback, and strips operators.**
   The strict pass requires every query term; it relaxes to partial matches *only when
   the strict pass returns nothing*. The consequence is counter-intuitive: retrieval gets
   worse as the corpus grows, because as soon as any one document matches every term,
   every partially-matching document is suppressed — including the one holding the answer.

   Measured on `sibyl-memory-client` 0.7.0. With a lone document missing the term
   `issue`, the query `"GPS system service issue"` still returns it. Add a second document
   containing all four terms and the same query returns only the new document; the first
   is dropped. `AND`/`OR`/`NOT` are sanitised away, so they cannot be used to widen the
   match; quoted phrases survive.

   Passing a whole question is therefore actively harmful in a realistic corpus, which is
   why the harness builds its candidate pool from unioned single-term searches scored by
   term coverage rather than from one question-shaped query.

## Things that would otherwise inflate the numbers

- **Evidence sessions are never truncated.** Clipping them removes the answer and depresses
  every arm equally, which hid the real effect in an early run.
- **Throttled calls are not scored as wrong.** Vertex returns `429 RESOURCE_EXHAUSTED`
  under concurrency. An early n=40 sweep scored 30 of 40 questions incorrect purely from
  throttling, which read as a catastrophic accuracy collapse. Calls now retry with
  exponential backoff; whatever still fails is counted as an error, excluded from the
  accuracy denominator, and the run exits non-zero above a 5% error rate.
- **The judge is blind to condition.** It sees only question, gold answer and prediction —
  never the retrieved context or which arm produced it.
- **Subsets are deterministic and stratified** by `question_type`, so `knowledge-update`
  questions — the ones poisoning actually targets — cannot be under-sampled by chance.

## Reproducing

```bash
make eval                                    # default subset
uv run python eval/run_utility.py --n 40 --poison-per-question 8 --k 8
```

The dataset downloads on first run into gitignored `demo-data/longmemeval/`. Poison is
cached to `demo-data/longmemeval/poison_cache.json` so runs are reproducible.
Every run writes a manifest (run id, dataset, model, k, contamination, cap utilisation,
error rate, wall clock) alongside the results.
