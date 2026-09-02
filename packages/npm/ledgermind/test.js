'use strict';
/** Cross-implementation vectors: these hashes come from Python `jcs` 0.2.1 + hashlib. */
const assert = require('assert');
const { canonicalize, contentHash, chainLink, verifyChain, GENESIS_HASH } = require('./index.js');

const VECTORS = {
  '4d4bbe59c6aad22442cde199a6a8a5f034405fcd78fb5a81c24ef249de1c45f1': { amount: 100 },
  '1c1d5afa7c9aa0010fd38b9520d5fedd1e4511e92d02db4bb83885b4dc48d415': { b: 1, a: 'x', c: [1, 2, { z: 1, y: 2 }] },
  '9c9cd7374542f060e5f4d0cbcc29d34ca5f61fb6efc5da9ea0a1c0762358e6e9': { k: 'unicode ünïcødé ✓', n: -3, f: 1.5, t: true, z: null },
  'fa5b8363938ab68e8b5ac9fb8af0a4e92349c910b5451f4f76f874243006f3ae': { nested: { deep: { list: [{ a: 1 }, { b: 2 }] } } },
};

for (const [expected, value] of Object.entries(VECTORS)) {
  assert.strictEqual(contentHash(value), expected, 'JCS vector mismatch for ' + JSON.stringify(value));
}

assert.strictEqual(canonicalize({ b: 1, a: 2 }), '{"a":2,"b":1}');
assert.strictEqual(canonicalize([1, 'a', null, true]), '[1,"a",null,true]');

// A two-link chain verifies, and any edit to a body breaks it at the right sequence.
const stamp = { agent_id: 'planner', timestamp: '2026-09-02T08:47:12Z', source_trust_tier: 'internal', evidence_ref: 'x' };
const b0 = { _content: { amount: 100 } };
const b1 = { _content: { amount: 200 } };
const h0 = chainLink(GENESIS_HASH, stamp, b0);
const h1 = chainLink(h0, stamp, b1);
const chain = [
  { tree: 't', sequence: 0, prev_hash: GENESIS_HASH, hash: h0, stamp: stamp, body: b0 },
  { tree: 't', sequence: 1, prev_hash: h0, hash: h1, stamp: stamp, body: b1 },
];

assert.strictEqual(verifyChain('t', chain).ok, true);
assert.strictEqual(verifyChain('t', []).ok, true);

const tampered = JSON.parse(JSON.stringify(chain));
tampered[1].body._content.amount = 201;
const broken = verifyChain('t', tampered);
assert.strictEqual(broken.ok, false);
assert.strictEqual(broken.brokenSequence, 1);

// Entries out of order must still verify by sequence.
assert.strictEqual(verifyChain('t', chain.slice().reverse()).ok, true);

console.log('ledgermind: all tests passed');
