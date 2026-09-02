#!/usr/bin/env bash
# Boot the demo UI and assert every beat route renders.
# CI missed a dead demo twice (missing python-multipart, then the Starlette 1.x
# TemplateResponse signature change) because it never launched the app. It does now.
set -euo pipefail

PORT="${SMOKE_PORT:-8799}"
ROUTES=(/ /congress /settlement /montage /diff /waitlist/count)

uv run uvicorn ui.app:app --port "$PORT" >/tmp/smoke_ui.log 2>&1 &
PID=$!
cleanup() { kill "$PID" 2>/dev/null || true; }
trap cleanup EXIT

for _ in $(seq 1 40); do
  curl -sf "http://127.0.0.1:$PORT/waitlist/count" >/dev/null 2>&1 && break
  sleep 0.5
done

FAILED=0
for route in "${ROUTES[@]}"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT$route")
  if [ "$code" = "200" ]; then
    printf '  OK   %-18s %s\n' "$route" "$code"
  else
    printf '  FAIL %-18s %s\n' "$route" "$code"
    FAILED=1
  fi
done

code=$(curl -s -o /dev/null -w '%{http_code}' -X POST \
  -F 'card_id=bank-details' -F 'text=' "http://127.0.0.1:$PORT/inject")
if [ "$code" = "200" ]; then printf '  OK   %-18s %s\n' "POST /inject" "$code"
else printf '  FAIL %-18s %s\n' "POST /inject" "$code"; FAILED=1; fi

if [ "$FAILED" -ne 0 ]; then
  echo "UI smoke FAILED — demo does not render. Log:" >&2
  tail -40 /tmp/smoke_ui.log >&2
  exit 1
fi
echo "UI smoke passed: demo boots and every beat route renders."
