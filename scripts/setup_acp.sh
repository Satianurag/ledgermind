#!/usr/bin/env bash
# ACP testnet one-time setup (Base Sepolia 84532).
# Uses a SEPARATE auth session from mainnet (IS_TESTNET=true → config-testnet.json).
set -euo pipefail
cd "$(dirname "$0")/.."

export IS_TESTNET=true

echo "=== Ledgermind ACP — Base Sepolia testnet ==="
echo "Note: testnet auth is separate from mainnet. You must sign in again."
echo ""

echo "=== Step 1: Authenticate (browser) ==="
echo "Run these two commands after opening the URL:"
echo "  npx acp configure start"
echo "  npx acp configure complete --request-id <requestId>"
echo ""

echo "=== Step 2: Create buyer agent + signer ==="
echo "  npx acp agent create --name ledgermind --description 'Ledgermind settlement client' --signer --policy restricted"
echo "  npx acp agent use --agent-id <agent-id-from-list>"
echo ""

echo "=== Step 3: Register on Base Sepolia ==="
echo "  npx acp agent register-erc8004 --chain-id 84532"
echo ""

echo "=== Step 4: Find a provider (browse) ==="
echo "  npx acp browse weather --chain-ids 84532 --top-k 5 --json"
echo "Copy walletAddress → ACP_PROVIDER_ADDRESS and offerings[0].name → ACP_OFFERING_NAME in .env"
echo ""

echo "=== Step 5: Fund agent wallet (testnet USDC) ==="
echo "  npx acp wallet address"
echo "  npx acp wallet balance --chain-id 84532"
echo "  npx acp wallet topup --chain-id 84532 --method coinbase --amount 2"
echo "  # or use CDP faucet USDC on the same address via make bootstrap-onchain"
echo ""

echo "=== Step 6: Bootstrap live receipts ==="
echo "  make bootstrap-onchain"
echo ""

if [[ "${1:-}" == "--start-auth" ]]; then
  npx acp configure start
fi
