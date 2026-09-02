# Demo video script (2–5 min)

Rules §08 requires a 2–5 minute video covering the problem and who has it, the product,
how it works, and how it uses Sibyl Memory — and it must include the fresh-session recall
beat. Rules §03 requires that beat to be **one continuous unedited segment with an
on-screen timestamp or commit hash**.

## Before recording

```bash
make reset && make seed      # clean memory; keeps the demo short and legible
make demo                    # API + production UI build
```

- Record at 1440×900 or larger. The evidence bar is small at 1080p downscales.
- The commit hash and UTC timestamp are pinned top-right in **every frame** — that is the
  §03 evidence, so never crop the top bar.
- Do **not** use `next dev`. It renders but does not hydrate in some environments.
- Close the `demo-data/onchain/wallet.json` file if it is open anywhere. It contains a
  plaintext testnet key.

---

## Shot list

### 0:00–0:25 — The problem

> "A team of AI agents shares one memory. One of them writes a fact that is wrong — or
> planted. Nothing in that memory says who wrote it, nothing proves it wasn't changed
> afterwards, and the last writer silently wins. In a payments back office that moves real
> money."

Show the Northwind Pay case in the evidence bar: CASE-2214, Meridian payout exception.

### 0:25–1:10 — Beat 1, the gate (**must be one unedited take**)

Kill the process on camera, then start it fresh.

> "This session has just opened. Nothing is in process memory."

Land on **Fresh recall**. Point at the top-right commit hash and timestamp.

> "It reads four tiers back out of Sibyl — the assignment, the counterparty's history,
> the journal, the payout policy — and chooses the reliable vendor. Remove that one
> memory item and the same code chooses the cheapest vendor instead. The decision is
> downstream of memory, not of the prompt."

Read the counterfactual line out loud. **Do not cut anywhere inside this segment.**

### 1:10–1:45 — Beat 2, integrity

Open **Receipt chain**.

> "Every governed write is stamped with who wrote it, when, from what source, and against
> what evidence — then hash-linked to its predecessor. The chain lives inside Sibyl
> itself; there is no second database. Change one byte of one body and every link after it
> breaks, and verification names the first one."

Optional, strong: run `npx ledgermind verify chain.json` in a terminal, edit one digit,
run it again and show it break.

### 1:45–2:30 — Beat 3, adjudication (the signature)

Open **Dispute congress** → *Open dispute*.

> "The worker recorded the payout as released. The auditor recorded it as held. Last-write-
> wins would overwrite one and lose the conflict entirely. Instead both survive: one
> upheld, one superseded, both still addressable by content hash. The arbiter may cite
> only chain-verified records — a citation that fails verification aborts the resolution —
> and the outcome is signed."

Let the two panels sit on screen. This is the frame that carries the idea.

### 2:30–3:05 — Beat 4, adversarial

Open **The heist** → *Trusted-source bank change*.

> "Poison arriving through a trusted channel. Watch which paths fire. The content
> heuristic is listed but marked advisory and never counts as a catch — content screening
> cannot detect a plainly worded false assertion, and a defense that pretends otherwise
> is measuring itself."

Then *Hostile injection* to show source-trust quarantine firing.

### 3:05–3:45 — Beat 5, settlement

Open **Settlement** → *Load receipts*.

> "A real x402 payment on Base Sepolia — click through to the explorer. The spend cap is
> not a constant: it is read from the REFERENCE tier before every payment. $2.50 is
> refused against the remembered $2.00 cap; $0.50 passes. Change the remembered policy and
> the wallet's behaviour changes."

Note the honest absence: ACP is reported as not exercised, never synthesised.

### 3:45–4:15 — Why it holds up

> "We replaced our own attack-success-rate metric because it was measuring the wrong
> thing. On LongMemEval at 2% contamination, undefended memory retains 21% of its utility.
> Additive provenance weighting does not help — under flooding it scores worse than no
> defense at all. Bounding how much untrusted content reaches the context fixes retrieval
> but not correctness. Adjudication retains 89%."

> "Delete Sibyl and all of this stops. It is the only read/write path in the codebase."

---

## Non-negotiables

1. The fresh-session segment is one continuous take with the commit hash visible.
2. Never claim ACP unless a real job has settled.
3. Show the x402 **transaction** page, not the wallet address page — the payment is
   gasless and relayed, so the payer's own transaction count reads 0.
