# ledgermind

Standalone verifier for [Ledgermind](https://github.com/Satianurag/ledgermind) receipt
chains. Zero dependencies, Node 18+.

A tamper-evident log is only worth something if you can check it **without trusting the
tool that produced it**. This is a deliberately independent reimplementation of the
chain: it recomputes every SHA-256 link over RFC 8785 canonical JSON and names the first
one that does not match. Its hashes are pinned against Python `jcs` 0.2.1 in `test.js`.

## Install

```bash
npm install -g ledgermind
```

## Use

Export a chain from a Ledgermind deployment, then verify it anywhere:

```bash
uv run ledgermind export-chain --out chain.json   # in the Ledgermind repo
ledgermind verify chain.json
```

```
  OK    warm:planner:case/CASE-2214  (3 links)
  BROKEN warm:worker:journal/payout-status
         first bad link at sequence 2
         expected 9dc82320790a4367dd916303206109fbdadf0678045325dd9b557e2c70ef0522
         actual   71c5236351459684530b8a6b21a38e4db4270d8849edf63824c9851833f4989c

21 tree(s), 1 broken
```

Exits `0` when every chain is intact, `1` when any link is broken, `2` on usage errors —
so it drops into CI as a guard.

`ledgermind hash <file.json>` prints the RFC 8785 content hash of any JSON document.

## API

```js
const { verifyChain, verifyAll, contentHash, canonicalize } = require('ledgermind');

verifyAll(entries);            // [{ ok, tree, entriesChecked, brokenSequence, ... }]
verifyChain('tree', entries);  // one tree
contentHash({ amount: 100 });  // sha256 over RFC 8785 canonical form
```

## Chain format

Each entry links to its predecessor:

```
hash = sha256( prev_hash_utf8 || RFC8785({ stamp, body }) )
```

with the genesis hash being 64 zeros. `stamp` carries `(agent_id, timestamp,
source_trust_tier, evidence_ref)`.

## License

MIT
