#!/usr/bin/env bash
# Run the full demo: FastAPI governance API + Next.js front end.
#
# Uses `next build && next start` rather than `next dev`. The dev server's HMR websocket
# does not connect in every environment, and when it fails the page renders but never
# hydrates -- no effects run, so the beats stay empty. A production build has no such
# dependency, and it is what the demo should be recorded against anyway.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_PORT="${API_PORT:-8787}"
WEB_PORT="${WEB_PORT:-3000}"
export NEXT_PUBLIC_API_BASE="http://127.0.0.1:${API_PORT}"

cd "$ROOT"

if [ ! -d web/node_modules ]; then
  echo "==> installing web dependencies"
  (cd web && npm install --silent)
fi

echo "==> starting governance API on :${API_PORT}"
uv run uvicorn ui.app:app --port "$API_PORT" > /tmp/ledgermind-api.log 2>&1 &
API_PID=$!

cleanup() { kill "$API_PID" "${WEB_PID:-}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

for _ in $(seq 1 40); do
  curl -sf "http://127.0.0.1:${API_PORT}/api/state" >/dev/null 2>&1 && break
  sleep 0.5
done

echo "==> building front end"
(cd web && npx next build > /tmp/ledgermind-web-build.log 2>&1) || {
  echo "front-end build failed; see /tmp/ledgermind-web-build.log" >&2
  tail -30 /tmp/ledgermind-web-build.log >&2
  exit 1
}

echo "==> starting front end on :${WEB_PORT}"
(cd web && npx next start --port "$WEB_PORT") &
WEB_PID=$!

for _ in $(seq 1 60); do
  curl -sf "http://127.0.0.1:${WEB_PORT}/" >/dev/null 2>&1 && break
  sleep 0.5
done

echo
echo "  demo:        http://localhost:${WEB_PORT}"
echo "  api:         http://127.0.0.1:${API_PORT}/api/state"
echo "  fallback ui: http://127.0.0.1:${API_PORT}/"
echo
echo "Ctrl-C to stop both."
wait "$WEB_PID"
