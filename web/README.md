# Ledgermind demo front end

Next.js 16 + shadcn/ui surface for the [Ledgermind](../README.md) governance layer. It
renders live data from the FastAPI governance API; it holds no state of its own.

## Run

From the repository root:

```bash
make demo          # seeds memory, starts the API, builds and serves this app
```

Then open http://localhost:3000.

Run it directly against an already-running API:

```bash
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8787 npx next build && npx next start
```

## Why `next build && next start` rather than `next dev`

The dev server's HMR websocket does not connect in every environment. When it fails the
page still renders server HTML but never hydrates — no effects run, so every beat stays
empty and buttons do nothing. A production build has no such dependency, and the demo
should be recorded against one anyway. `scripts/demo.sh` does this for you.

## Layout

`src/lib/api.ts` is the typed client. Each beat is a component in `src/components/beats/`:

| component | beat |
|---|---|
| `recall-panel` | fresh-session recall — commit hash, recalled memory, decision flip |
| `chain-panel` | receipt chain, provenance stamps, tier counts, verification |
| `heist-panel` | poison injection and which defense paths fired |
| `congress-panel` | dispute with both versions visible, arbiter, signed receipt |
| `settlement-panel` | Base receipts, memory-governed cap, counterfactual replay |
