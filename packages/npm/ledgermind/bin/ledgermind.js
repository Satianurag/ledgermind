#!/usr/bin/env node
/** npm i ledgermind — wraps Python governance CLI (PMF artifact #1) */
const { spawnSync } = require('child_process');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const args = process.argv.slice(2);

function run(cmd, cmdArgs, opts = {}) {
  const r = spawnSync(cmd, cmdArgs, { stdio: 'inherit', cwd: ROOT, ...opts });
  if (r.status !== 0) process.exit(r.status ?? 1);
}

if (args[0] === 'demo' || args.includes('--catch-poison')) {
  run('uv', ['run', 'python', 'demo/reset_demo.py']);
  run('uv', ['run', 'python', 'demo/seed_case_2214.py']);
  run('uv', ['run', 'ledgermind', 'catch-poison']);
} else if (args[0] === 'verify') {
  run('uv', ['run', 'ledgermind', 'verify', ...args.slice(1)]);
} else if (args[0] === 'eval') {
  run('uv', ['run', 'python', 'eval/run_asr.py']);
} else {
  run('uv', ['run', 'ledgermind', ...args]);
}
