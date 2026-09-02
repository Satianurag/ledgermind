#!/usr/bin/env node
'use strict';
const fs = require('fs');
const { verifyAll, contentHash } = require('../index.js');

const USAGE = `ledgermind — verify Ledgermind receipt chains

  ledgermind verify <chain.json>   recompute every link; exit 1 if any is broken
  ledgermind hash <file.json>      print the RFC 8785 content hash of a JSON file

Export a chain with:  uv run ledgermind export-chain > chain.json
`;

function readJson(path) {
  try {
    return JSON.parse(fs.readFileSync(path, 'utf8'));
  } catch (err) {
    console.error('cannot read ' + path + ': ' + err.message);
    process.exit(2);
  }
}

const [command, target] = process.argv.slice(2);

if (!command || command === '-h' || command === '--help') {
  process.stdout.write(USAGE);
  process.exit(0);
}

if (command === 'verify') {
  if (!target) { console.error('usage: ledgermind verify <chain.json>'); process.exit(2); }
  const data = readJson(target);
  const entries = Array.isArray(data) ? data : data.entries || [];
  if (entries.length === 0) { console.error('no chain entries found in ' + target); process.exit(2); }
  const results = verifyAll(entries);
  let broken = 0;
  for (const r of results) {
    if (r.ok) {
      console.log('  OK    ' + r.tree + '  (' + r.entriesChecked + ' links)');
    } else {
      broken += 1;
      console.log('  BROKEN ' + r.tree);
      console.log('         first bad link at sequence ' + r.brokenSequence);
      console.log('         expected ' + r.expectedHash);
      console.log('         actual   ' + r.actualHash);
    }
  }
  console.log('\n' + results.length + ' tree(s), ' + broken + ' broken');
  process.exit(broken === 0 ? 0 : 1);
}

if (command === 'hash') {
  if (!target) { console.error('usage: ledgermind hash <file.json>'); process.exit(2); }
  console.log(contentHash(readJson(target)));
  process.exit(0);
}

console.error('unknown command: ' + command);
process.stdout.write(USAGE);
process.exit(2);
