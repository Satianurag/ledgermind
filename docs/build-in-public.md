# Build-in-public posts (draft)

Rules §08 requires **two public posts**: the demo video and at least one build log,
tagging **@sibylcap** and each claimed partner.

Claimed partners as of now: **Base**. Do **not** tag Virtuals unless an ACP job has
actually settled — §06 penalises a claimed stack that was not exercised, and tagging them
is a claim.

---

## Post 1 — build log

> Spent the build window on one question: when two agents remember contradictory things,
> who wins?
>
> The default answer is last-write-wins. The earlier claim is overwritten and the conflict
> disappears — which is exactly how a poisoned fact moves money.
>
> Ledgermind makes that a dispute instead. Both versions survive, hash-linked and
> attributable. An arbiter may cite only chain-verified records; a citation that fails
> verification aborts the resolution.
>
> Three things I found building it on @sibylcap Sibyl Memory:
>
> • The free tier is a hard 5 MiB, not the 2 MB the docs state — raised 2026-08-06. It is
>   per *account*, not per database, and summed across every store an agent can resolve.
> • Stored size is ~7× raw text once FTS5 and the search shadow are counted. The cap holds
>   under 1 MB of text.
> • `search()` joins query terms conjunctively, so passing a whole question drops any
>   document missing one word — the evidence session is usually never retrieved at all.
>
> All three shaped the architecture. Details and repro in the repo.
>
> github.com/Satianurag/ledgermind

*(Tag @sibylcap. Add @base only if the post mentions the onchain settlement.)*

---

## Post 2 — demo video

> Ledgermind: governed coordination memory for agent teams. Demo below.
>
> A fresh session — nothing in process memory — reads four Sibyl tiers and flips a payout
> decision from cheapest vendor to reliable vendor. Delete the memory and the same code
> makes the opposite call.
>
> I also threw out my own security metric. The first harness reported "ASR 41% → 10%".
> That baseline was measuring the SQLite tokenizer, and the denominator included clean
> controls. Rebuilt on LongMemEval measuring utility retained instead:
>
> • undefended, 2% contamination → 21% utility retained
> • additive provenance weighting → 16%, *worse than no defense*
> • bounded occupancy → fixes retrieval, not correctness
> • adjudication → 89%
>
> Bounding how much untrusted content reaches the context gets the true record back into
> the context. It does not make the model believe it. That takes adjudication.
>
> Settlement runs on @base — real x402 payment on Sepolia, and the wallet's spend cap is
> read from memory before every payment rather than hardcoded.
>
> Built on @sibylcap Sibyl Memory for the Sibyl Labs Hackathon.
>
> github.com/Satianurag/ledgermind

---

## Notes

- Keep the numbers exactly as reported in `eval/output/`. Do not round 88.9% up to 90%.
- The Sibyl findings in post 1 are genuinely useful to their team and are the strongest
  reason for them to engage — lead with those rather than with the product pitch.
- If ACP settles before posting, add @virtuals_io and one line naming the job.
