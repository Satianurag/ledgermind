# Ledgermind

Governed coordination memory for agent teams — provenance-stamped, tamper-evident, dispute-resolved with signed receipts, and settled on Base.

Built on [Sibyl Memory](https://docs.sibyllabs.org/memory/tiers) for the Sibyl Labs Hackathon (Sep 1–10, 2026).

## Where memory is load-bearing (< 2 min)

All agent reads and writes flow through the **governance layer** — the only code path to Sibyl:

| Location | Role |
|----------|------|
| [`packages/python/ledgermind/ledgermind/store.py`](packages/python/ledgermind/ledgermind/store.py) | `GovernedMemoryClient` — sole Sibyl SDK import |
| [`packages/python/ledgermind/ledgermind/chain.py`](packages/python/ledgermind/ledgermind/chain.py) | SHA-256 receipt chain per memory tree |
| [`demo/seed_case_2214.py`](demo/seed_case_2214.py) | CASE-2214 demo data into five Sibyl tiers |

**Deletion test:** stub Sibyl in CI → all three agents fail at first memory op (`tests/test_deletion.py`).

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

## npm package

```bash
npm install -g ./packages/npm/ledgermind
ledgermind demo --catch-poison
```

## Eval harness

```bash
make eval   # poisoning ASR: vanilla Sibyl vs Ledgermind
```

| Metric | Value (22-input gauntlet) |
|--------|---------------------------|
| Baseline ASR (vanilla) | ~41% |
| Governed ASR (Ledgermind) | **≤10%** |
| Command | `make eval` |

Results manifest: `eval/output/asr_report.json`

## Partner stacks

- **Base:** Agentic Wallet (`cdp-sdk`), x402 payments, B20 read — [`onchain/`](onchain/)
- **Virtuals:** ACP client job via `acp-cli` subprocess — [`onchain/acp.py`](onchain/acp.py)
- **Vertex AI:** Gemini models only — [`packages/python/ledgermind/ledgermind/vertex.py`](packages/python/ledgermind/ledgermind/vertex.py)

## License

MIT
