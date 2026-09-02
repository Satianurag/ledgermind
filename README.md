# Ledgermind

Governed coordination memory for agent teams — provenance-stamped, tamper-evident, dispute-resolved with signed receipts, and settled on Base.

Built on [Sibyl Memory](https://docs.sibyllabs.org/memory/tiers) for the Sibyl Labs Hackathon (Sep 1–10, 2026).

## Where memory is load-bearing (< 2 min)

All agent reads and writes flow through the **governance layer** — the only code path to Sibyl:

| Location | Role |
|----------|------|
| [`packages/python/ledgermind/ledgermind/store.py`](packages/python/ledgermind/ledgermind/store.py) | `GovernedMemoryClient` — the **only** `sibyl_memory_client` import in the codebase |
| [`packages/python/ledgermind/ledgermind/chain.py`](packages/python/ledgermind/ledgermind/chain.py) | SHA-256 receipt chain per memory tree, over RFC 8785 canonical JSON |
| [`agents/graph.py`](agents/graph.py) | Three agents whose every decision is read back out of Sibyl |
| [`packages/python/ledgermind/ledgermind/dispute.py`](packages/python/ledgermind/ledgermind/dispute.py) | Contradiction opens a dispute instead of overwriting the prior record |
| [`demo/seed_case_2214.py`](demo/seed_case_2214.py) | CASE-2214 demo data across all five Sibyl tiers |

Nothing in `agents/graph.py` restates the case file from a literal. The payout amount comes
from the WARM case entity, the approval threshold from the REFERENCE policy, and the
contradiction that opens the dispute is *detected* by comparing two COLD journal records.

**Deletion test:** stub Sibyl in CI → all three agents fail at their first memory op
([`tests/test_deletion.py`](tests/test_deletion.py)). Two further tests make the claim
falsifiable rather than assertable: the same graph must reach a *different* payout decision
when memory holds a different amount, and a dispute must open *only* when two remembered
records actually disagree ([`tests/test_langgraph.py`](tests/test_langgraph.py)).

## Quick start

```bash
cp .env.example .env   # set GOOGLE_CLOUD_PROJECT
gcloud auth application-default login
make sync
make reset && make seed
make test
make demo              # FastAPI UI on :8787
```

## Onchain settlement (Base Sepolia testnet — $0)

All settlement receipts use **Base Sepolia** (chain 84532). CDP faucet funds the wallet; x402 and ACP run on testnet. B20 is a **read-only mainnet** `eth_call` (PRD allows this; no mainnet spend).

```bash
# 1. CDP keys in .env (portal.cdp.coinbase.com)
# 2. ACP testnet setup (separate login from mainnet):
make setup-acp
#    then: IS_TESTNET=true npx acp configure start → complete → agent create
#    set ACP_PROVIDER_ADDRESS + ACP_OFFERING_NAME in .env from browse output
# 3. Full settlement prerun:
make bootstrap-onchain
make reset && make seed
```

Receipts land in `demo-data/onchain/` with judge-clickable Sepolia explorer URLs (B20 links to mainnet token page).

## npm package — independent chain verifier

A tamper-evident log is only worth something if a third party can check it *without
trusting the tool that produced it*. [`packages/npm/ledgermind`](packages/npm/ledgermind)
is a zero-dependency reimplementation of RFC 8785 canonicalisation and the SHA-256 link
function, cross-validated against Python `jcs` 0.2.1 in CI.

```bash
uv run ledgermind export-chain --out chain.json
npx ledgermind verify chain.json
```

```
  OK    warm:planner:case/CASE-2214  (3 links)
  BROKEN warm:worker:journal/payout-status
         first bad link at sequence 2
```

Exits `1` on a broken link, so it drops into CI as a guard. Changing one digit of one
remembered amount is caught and located.

## Eval harness

```bash
make eval                                              # default subset
uv run python eval/run_utility.py --n 40 --k 8         # as reported below
```

Methodology, threat model and the measured Sibyl constraints:
[`docs/eval-methodology.md`](docs/eval-methodology.md).

ASR was dropped as the headline metric. Per
[arXiv 2608.21230](https://arxiv.org/abs/2608.21230) it "cannot distinguish a memory that
resisted an attack from one the attack rendered useless" — a defense that quarantines
everything scores perfectly and destroys the product. We report **utility retained**
(poisoned accuracy ÷ clean accuracy) on [LongMemEval](https://github.com/xiaowu0162/LongMemEval),
the benchmark Sibyl itself reports against.

**40 questions, k=8, 2.10% corpus contamination,
one false memory per question, `gemini-3.5-flash`. API error rate 2.5%, excluded from accuracy
rather than scored as wrong.**

| gate | clean | poisoned | utility retained | Corpus N | poison occupancy |
|---|---|---|---|---|---|
| `none` | 0.475 | 0.100 | **21.1%** | 0.051 | 0.138 |
| `provenance_weighted` | 0.475 | 0.125 | **26.3%** | 0.103 | 0.119 |
| `bounded_occupancy` | 0.475 | 0.125 | **26.3%** | 0.125 | 0.125 |
| `adjudicated` | 0.462 | 0.410 | **88.9%** | 0.359 | 0.125 |

- `none` — no provenance signal. Utility collapses to 21%.
- `provenance_weighted` — additive trust penalty. Barely moves, reproducing the paper's
  finding that additive weighting has "no usable middle ground".
- `bounded_occupancy` — provenance reserves retrieval capacity instead of penalising score.
  This is, as far as we can tell, the first implementation of the gate that paper proposes
  and states it did not build. Against a *single* false memory the cap does not bind
  (1 of 8 slots is already under a 20% ceiling), so it barely helps — an honest null we
  report rather than hide. Its value shows under flooding, where it cuts poison occupancy
  from 0.875 to 0.125 and restores evidence recall from 0.125 to 1.000.
- `adjudicated` — bounded occupancy plus provenance-aware answering, where a chain-verified
  internal record beats a contradicting external one. **89%
  utility retained.**

**Corpus N** is the fairness test: a fraction of *genuine* evidence is itself marked
untrusted. Any provenance defense looks perfect by excluding all untrusted content, and
Corpus N is where hard filtering destroys the answer along with the attack. Adjudication
scores 0.359 there against 0.051
undefended.

The result that matters is the *shape*: bounding how much untrusted content reaches the
context fixes retrieval but not correctness — one false memory beside the true one still
flips the answer. Adjudication is what recovers utility. That is the thesis of this
project, measured rather than asserted.

Clean accuracy is 0.475 rather than the ~0.85 reported in the
literature because Sibyl is zero-embedding: retrieval is FTS5 term matching, not vector
similarity. The comparison across arms is unaffected — every arm reads the identical store.

### Under a flooding adversary

An attacker with write access can restate the same false memory as often as it likes.
`--poison-per-question 8` is that budget: 14.64% contamination,
same 40 questions, 2.5% API error rate.

| gate | clean | poisoned | utility retained | poison occupancy | evidence recall |
|---|---|---|---|---|---|
| `none` | 0.450 | 0.100 | **22.2%** | 0.875 | 0.275 |
| `provenance_weighted` | 0.475 | 0.077 | **16.2%** | 0.819 | 0.375 |
| `bounded_occupancy` | 0.450 | 0.125 | **27.8%** | 0.125 | 0.875 |
| `adjudicated` | 0.462 | 0.410 | **88.9%** | 0.125 | 0.875 |

This is where the gate earns its place. Undefended, the flood takes **87.5%
of the retrieved context** and evidence recall falls to 0.275.
Bounded occupancy holds the attacker to 12.5% and
restores evidence recall to 0.875 — but
utility only reaches 27.8%, because getting the
true record back into context is not the same as being believed. Adjudication takes that to
88.9%.

Note that additive provenance weighting scores **16.2%,
below the 22.2% of no defense at all** — it reshuffles ranking
without displacing the flood, and pays for it. That is the "no usable middle ground" result
from arXiv 2608.21230 reproduced on a different substrate.

Every run writes a manifest (run id, dataset, model, k, contamination, cap utilisation,
error rate, wall clock) to `eval/output/`.

## Partner stacks

**Base — exercised.** A real x402 payment settled on Base Sepolia: EIP-3009
`transferWithAuthorization` of 0.001 USDC, status success. Verify it yourself:

> [`0xc85049e1927f79c565b61a8ab7c824aa7ffb10b2e07b30deb067f6745416005a`](https://sepolia.basescan.org/tx/0xc85049e1927f79c565b61a8ab7c824aa7ffb10b2e07b30deb067f6745416005a)

Note the payment is gasless and facilitator-relayed, so the payer wallet's own
transaction count is 0 — the evidence is the transaction, not the address.

Chain-head checkpoints are anchored on Base Sepolia as self-transfers carrying the head in
calldata, e.g.
[`0xbf639388…`](https://sepolia.basescan.org/tx/0xbf639388be7c61f35c9abe3191b73b0b203db0b21bc4fd62989d919a8c74805b)
(status success, block 46285791). An anchor attests what the chain head *was*; it does not
store tier state, so `RollbackManager.restore()` reports `restored: false` across a process
restart rather than claiming a recovery it cannot perform.

Also included: a capped Agentic Wallet whose cap is read from Sibyl REFERENCE before every
payment (`onchain/wallet.py`) — $2.50 is refused against the remembered $2.00 cap while
$0.50 passes — and a live B20 `eth_call` on Base mainnet (`onchain/b20.py`).
Code: [`onchain/`](onchain/)

**Virtuals — not yet exercised.** The ACP client is implemented
([`onchain/acp.py`](onchain/acp.py)) but no job has been run, so no receipt exists and
the settlement beat reports `unexercised_stacks: ["acp"]` rather than synthesising one.
This stack is not claimed until a real job settles.

**Vertex AI:** Gemini models only — [`packages/python/ledgermind/ledgermind/vertex.py`](packages/python/ledgermind/ledgermind/vertex.py)

## How memory made this possible

Ledgermind is not an agent that happens to save notes -- the memory *is* the product.
Three agents share one Sibyl tenant, and every read and write crosses a single governance
boundary (`GovernedMemoryClient`), so what one agent recorded is what another agent is
later judged against. That makes three things possible that are impossible without
persistent memory:

- **Adjudication instead of last-write-wins.** A dispute needs two conflicting records
  that both still exist. Sibyl's append-only journal and `UNIQUE (tenant_id, category,
  name)` constraint mean the earlier claim is never silently overwritten, so the arbiter
  has something to adjudicate and can cite it by content hash.
- **Tamper-evidence across sessions.** The SHA-256 receipt chain lives *inside* Sibyl at
  HOT state keys. Verification re-walks the stored chain, so integrity survives process
  restarts -- there is no in-RAM shadow copy to trust.
- **A commercial decision that changes on recall.** In a genuinely fresh session the
  vendor choice flips from cheapest to reliable, because the counterparty's late-delivery
  history and the settlement receipts are read back out of memory. Delete the memory and
  the decision reverts to the cheapest-vendor default.

Remove Sibyl and all three collapse at the first memory operation -- demonstrated in CI
by `tests/test_deletion.py`.

## Prior work

Ledgermind targets **OWASP ASI06 -- Memory and Context Poisoning**, added to the 2026
OWASP Top 10 for Agentic Applications. Related work we build alongside rather than claim
as novel:

| Project / paper | Overlap | What Ledgermind adds |
|---|---|---|
| [OWASP Agent Memory Guard](https://owasp.org/www-project-agent-memory-guard/) (incubator, v0.0.0) | SHA-256 memory integrity, declarative write policies, snapshot/rollback | Multi-agent adjudication with signed receipts; onchain settlement evidence |
| [arXiv 2608.21230](https://arxiv.org/abs/2608.21230) -- limits of content screening and provenance ranking | Shows both defenses we started from are structurally limited | Implements the bounded-occupancy provenance gate that paper calls for and states it did not build |
| [arXiv 2601.05504](https://arxiv.org/abs/2601.05504) -- memory poisoning attack/defense | Trust-aware sanitization, composite trust scoring | Keeps the conflicting record instead of sanitising it away, and adjudicates |
| Mem0 / Zep / Letta / LangMem | Persistent agent memory substrates | Governance layer, not a memory store; Sibyl-native, zero-embedding |

Our claim is narrow and specific: **not** that we detect poison better than the field,
but that adjudication-with-receipts is a different axis from screening and ranking. When
you cannot tell a true assertion from a false one by reading it -- which 2608.21230 shows
you generally cannot -- the durable answer is to refuse to destroy the prior fact and to
make the conflict an auditable, receipted event.

## Security note

`demo-data/` is gitignored and never committed. It contains `onchain/wallet.json` with a
**plaintext Base Sepolia private key** used for testnet settlement. Do not fund that
address on mainnet, and do not open that file on screen during a demo.

## License

MIT
