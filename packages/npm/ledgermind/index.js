'use strict';
/**
 * Standalone verifier for Ledgermind receipt chains.
 *
 * No dependencies and no Python: given an exported chain JSON, this recomputes every
 * link and names the first one that breaks. That is the point of a tamper-evident log --
 * anyone holding the export must be able to check it without trusting the tool that
 * produced it, so this is a deliberately independent reimplementation.
 */
const crypto = require('crypto');

const GENESIS_HASH = '0'.repeat(64);

/**
 * RFC 8785 (JCS) canonicalization.
 *
 * Object keys sort by UTF-16 code unit, which is what Array.prototype.sort does by
 * default, and matches Python's `jcs` package. Integers and ordinary decimals serialize
 * identically under JSON.stringify and Python's json, so the two implementations agree
 * on every payload this format carries.
 */
function canonicalize(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'number') {
    if (typeof value === 'number' && !Number.isFinite(value)) {
      throw new TypeError('non-finite numbers cannot be canonicalized');
    }
    return JSON.stringify(value);
  }
  if (typeof value === 'string') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonicalize).join(',') + ']';
  if (typeof value === 'object') {
    const keys = Object.keys(value).filter((k) => value[k] !== undefined).sort();
    return '{' + keys.map((k) => JSON.stringify(k) + ':' + canonicalize(value[k])).join(',') + '}';
  }
  throw new TypeError('cannot canonicalize ' + typeof value);
}

function sha256Hex(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

/** hash = sha256(prev_hash_utf8 || jcs({stamp, body})) */
function chainLink(prevHash, stamp, body) {
  const envelope = canonicalize({ stamp: stamp, body: body });
  return sha256Hex(Buffer.concat([Buffer.from(prevHash, 'utf8'), Buffer.from(envelope, 'utf8')]));
}

function contentHash(body) {
  return sha256Hex(Buffer.from(canonicalize(body), 'utf8'));
}

/** Verify one tree's entries in sequence order. */
function verifyChain(tree, entries) {
  if (!entries || entries.length === 0) {
    return { ok: true, tree: tree, entriesChecked: 0, message: 'empty chain' };
  }
  const sorted = entries.slice().sort((a, b) => (a.sequence || 0) - (b.sequence || 0));
  let prevHash = GENESIS_HASH;
  for (let i = 0; i < sorted.length; i += 1) {
    const entry = sorted[i];
    const expected = chainLink(prevHash, entry.stamp || {}, entry.body || {});
    if (entry.hash !== expected) {
      return {
        ok: false,
        tree: tree,
        entriesChecked: i,
        brokenSequence: entry.sequence !== undefined ? entry.sequence : i,
        expectedHash: expected,
        actualHash: entry.hash || '',
        message: 'broken link at sequence ' + (entry.sequence !== undefined ? entry.sequence : i),
      };
    }
    prevHash = entry.hash;
  }
  return { ok: true, tree: tree, entriesChecked: sorted.length, message: 'chain intact' };
}

/** Verify every tree in a flat list of entries. */
function verifyAll(entries) {
  const byTree = new Map();
  for (const entry of entries || []) {
    const tree = entry.tree || '';
    if (!byTree.has(tree)) byTree.set(tree, []);
    byTree.get(tree).push(entry);
  }
  return Array.from(byTree.keys()).sort().map((tree) => verifyChain(tree, byTree.get(tree)));
}

module.exports = { GENESIS_HASH, canonicalize, chainLink, contentHash, verifyChain, verifyAll };
