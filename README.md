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
make eval   # 22-input poisoning gauntlet, vanilla Sibyl vs Ledgermind
```

**Status: being rebuilt (Sep 2026).** The current gauntlet reports an attack-success
rate over a denominator that includes clean controls, which flatters both arms, and its
content-detection path is a keyword match rather than a semantic one. Those numbers are
not defensible, so they are not quoted here.

The replacement follows the published methodology in
[arXiv 2608.21230](https://arxiv.org/abs/2608.21230): **utility retained** (poisoned
accuracy / clean accuracy) on a [LongMemEval](https://github.com/xiaowu0162/LongMemEval)
subset at ~1.2% corpus contamination, reported alongside the false-positive rate on
benign untrusted content. ASR is deliberately dropped as the primary metric -- it
"cannot distinguish a memory that resisted an attack from one the attack rendered
useless."

Results manifest: `eval/output/asr_report.json`

## Partner stacks

**Base — exercised.** A real x402 payment settled on Base Sepolia: EIP-3009
`transferWithAuthorization` of 0.001 USDC, status success. Verify it yourself:

> [`0xc85049e1927f79c565b61a8ab7c824aa7ffb10b2e07b30deb067f6745416005a`](https://sepolia.basescan.org/tx/0xc85049e1927f79c565b61a8ab7c824aa7ffb10b2e07b30deb067f6745416005a)

Note the payment is gasless and facilitator-relayed, so the payer wallet's own
transaction count is 0 — the evidence is the transaction, not the address. Also included:
a capped Agentic Wallet whose cap is read from Sibyl REFERENCE before every payment
(`onchain/wallet.py`), and a live B20 `eth_call` on Base mainnet (`onchain/b20.py`).
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
