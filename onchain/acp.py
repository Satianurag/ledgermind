"""Virtuals ACP client job via acp-cli subprocess (PRD §6.6) — Base Sepolia testnet."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from onchain.network import acp_subprocess_env, explorer_tx_url, load_network_env

RECEIPTS_DIR = Path(__file__).resolve().parents[1] / "demo-data" / "onchain"
ACP_RECEIPT_FILE = RECEIPTS_DIR / "acp_receipt.json"
ROOT = Path(__file__).resolve().parents[1]


def _acp_bin() -> str:
    local = ROOT / "node_modules" / ".bin" / "acp"
    if local.exists():
        return str(local)
    return "acp"


def run_acp_cli(args: list[str], *, timeout: int = 180) -> dict[str, Any]:
    """Invoke acp-cli as subprocess (IS_TESTNET=true → api-dev + config-testnet.json)."""
    try:
        result = subprocess.run(
            [_acp_bin(), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=str(ROOT),
            env=acp_subprocess_env(),
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except FileNotFoundError:
        return {"ok": False, "error": "acp-cli not installed — run npm install in repo root"}


def _cli_failure_message(result: dict[str, Any]) -> str:
    payload = _parse_json(result.get("stdout", ""))
    if isinstance(payload, dict) and payload.get("error"):
        return str(payload["error"])[:400]
    stderr = (result.get("stderr") or "").strip()
    if stderr:
        return stderr[:400]
    return f"exit code {result.get('returncode')}"


def _parse_json(stdout: str) -> dict[str, Any] | None:
    stdout = stdout.strip()
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stdout, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def _extract_tx_hash(payload: dict[str, Any] | None) -> str:
    if not payload:
        return ""
    for key in ("txHash", "tx_hash", "transactionHash", "fundTxHash", "settleTxHash"):
        if payload.get(key):
            return str(payload[key])
    for nested in ("fund", "settle", "transaction", "receipt"):
        sub = payload.get(nested)
        if isinstance(sub, dict):
            tx = _extract_tx_hash(sub)
            if tx:
                return tx
    return ""


def _is_configured() -> bool:
    if os.environ.get("ACP_ACCESS_TOKEN"):
        return True
    status = run_acp_cli(["wallet", "address"])
    return status.get("ok") and "0x" in (status.get("stdout") or "")


def _browse_providers(chain_id: str) -> tuple[str, str]:
    for query in ("weather", "data", "agent"):
        browse = run_acp_cli(
            ["browse", query, "--chain-ids", chain_id, "--top-k", "5", "--json"],
        )
        if not browse.get("ok"):
            continue
        agents = _parse_json(browse.get("stdout", ""))
        items = (
            agents
            if isinstance(agents, list)
            else (agents or {}).get("data")
            or (agents or {}).get("agents")
            or []
        )
        for agent in items:
            offerings = agent.get("offerings") or agent.get("jobOfferings") or []
            if not offerings:
                continue
            provider = agent.get("walletAddress") or agent.get("address", "")
            offering = offerings[0].get("name", "")
            if provider and offering:
                return provider, offering
    return "", ""


def _requirements_for(offering: str) -> str:
    if custom := os.environ.get("ACP_REQUIREMENTS_JSON"):
        return custom
    if offering == "crypto_news":
        return '{"initiate_AI_crypto_news_report_job": true}'
    return '{"location":"Athens"}'


def _poll_fund_amount(job_id: str, chain_id: str, *, attempts: int = 60) -> str:
    fallback = os.environ.get("ACP_FUND_AMOUNT", "0.50")
    for _ in range(attempts):
        hist = run_acp_cli(
            ["job", "history", "--job-id", job_id, "--chain-id", chain_id, "--json"],
        )
        if hist.get("ok"):
            data = _parse_json(hist.get("stdout", "")) or {}
            for entry in reversed(data.get("entries") or []):
                event = entry.get("event") or {}
                if event.get("type") == "budget.set" and event.get("amount") is not None:
                    return str(event["amount"])
        time.sleep(2)
    return fallback


def load_persisted_receipt() -> dict[str, Any] | None:
    from onchain.receipts import is_live_receipt

    if ACP_RECEIPT_FILE.exists():
        receipt = json.loads(ACP_RECEIPT_FILE.read_text())
        if is_live_receipt(receipt):
            network = receipt.get("network", "")
            if network and "sepolia" not in network:
                return None
            return receipt
    return None


def _persist_receipt(receipt: dict[str, Any]) -> None:
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    ACP_RECEIPT_FILE.write_text(json.dumps(receipt, indent=2))


def execute_acp_job(*, force: bool = False) -> dict[str, Any]:
    """Create, fund, and complete an ACP job on Base Sepolia when CLI is configured."""
    load_network_env()

    if not force:
        persisted = load_persisted_receipt()
        if persisted:
            persisted["source"] = "persisted"
            return persisted

    if not _is_configured():
        raise RuntimeError(
            "ACP testnet not configured. Run: IS_TESTNET=true make setup-acp "
            "(separate login from mainnet — uses config-testnet.json)"
        )

    chain_id = os.environ.get("ACP_CHAIN_ID", "84532")
    if chain_id != "84532":
        raise RuntimeError(
            f"ACP_CHAIN_ID must be 84532 (Base Sepolia) for testnet demo, got {chain_id}"
        )

    provider = os.environ.get("ACP_PROVIDER_ADDRESS", "")
    offering = os.environ.get("ACP_OFFERING_NAME", "")
    if not provider or not offering:
        provider, offering = _browse_providers(chain_id)
    if not provider or not offering:
        raise RuntimeError(
            "No ACP provider on Base Sepolia. Run IS_TESTNET=true make setup-acp, "
            "then set ACP_PROVIDER_ADDRESS and ACP_OFFERING_NAME in .env from "
            "`npx acp browse weather --chain-ids 84532 --json`"
        )

    requirements = _requirements_for(offering)
    create = run_acp_cli(
        [
            "client",
            "create-job",
            "--provider",
            provider,
            "--offering-name",
            offering,
            "--requirements",
            requirements,
            "--chain-id",
            chain_id,
            "--json",
        ],
    )
    if not create.get("ok"):
        raise RuntimeError(f"acp create-job failed: {_cli_failure_message(create)}")

    created = _parse_json(create.get("stdout", "")) or {}
    job_id = str(created.get("jobId") or created.get("job_id") or created.get("id", ""))
    if not job_id:
        raise RuntimeError(f"Could not parse job id from: {create.get('stdout', '')[:400]}")

    amount = _poll_fund_amount(job_id, chain_id)
    fund = run_acp_cli(
        ["client", "fund", "--job-id", job_id, "--chain-id", chain_id, "--amount", amount, "--json"],
    )
    if not fund.get("ok"):
        raise RuntimeError(f"acp fund failed: {_cli_failure_message(fund)}")

    fund_data = _parse_json(fund.get("stdout", "")) or {}
    tx_hash = _extract_tx_hash(fund_data) or _extract_tx_hash(created)

    for _ in range(30):
        watch = run_acp_cli(["job", "watch", "--job-id", job_id, "--timeout", "10000", "--json"])
        if watch.get("ok"):
            complete = run_acp_cli(
                ["client", "complete", "--job-id", job_id, "--chain-id", chain_id, "--json"],
            )
            if complete.get("ok"):
                complete_data = _parse_json(complete.get("stdout", "")) or {}
                tx_hash = tx_hash or _extract_tx_hash(complete_data)
            break
        time.sleep(2)

    if not tx_hash:
        raise RuntimeError("ACP job ran but no onchain tx hash was captured")

    network = os.environ.get("ONCHAIN_NETWORK", "base-sepolia")
    receipt = {
        "kind": "acp",
        "job_id": job_id,
        "provider": provider,
        "offering": offering,
        "tx_hash": tx_hash,
        "explorer_url": explorer_tx_url(tx_hash),
        "executed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cli": "@virtuals-protocol/acp-cli",
        "network": network,
        "chain_id": int(chain_id),
        "os_virtuals_url": f"https://os.virtuals.io/acp/job/{job_id}",
        "source": "live",
        "create": created,
        "fund": fund_data,
    }
    _persist_receipt(receipt)
    return receipt


def execute_or_load_acp_job() -> dict[str, Any]:
    persisted = load_persisted_receipt()
    if persisted:
        return persisted
    return execute_acp_job(force=True)
