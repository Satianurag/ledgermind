"""FastAPI + htmx demo UI."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from ledgermind.config import get_settings
from ledgermind.decisions import build_decision_context, select_vendor
from ledgermind.defense import evaluate_injection
from ledgermind.diff import diff_snapshots, render_rich_table, snapshot_entities
from ledgermind.dispute import DisputeCongress
from ledgermind.rollback import RollbackManager
from ledgermind.store import GovernedMemoryClient
from ledgermind.telemetry import TelemetryLogger

from onchain import write_receipts_to_governance
from ui.poison_cards import POISON_CARDS

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

app = FastAPI(title="Ledgermind Demo", version="0.1.0")
_waitlist_count = 0


def _commit_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "dev"


def _gov() -> GovernedMemoryClient:
    return GovernedMemoryClient(get_settings().sibyl_memory_db)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        "index.html",
        {
            "request": request,
            "commit": _commit_hash(),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "poison_cards": POISON_CARDS,
        },
    )


@app.post("/inject", response_class=HTMLResponse)
async def inject(
    request: Request,
    card_id: str = Form(...),
    text: str = Form(""),
) -> HTMLResponse:
    card = next((c for c in POISON_CARDS if c["id"] == card_id), POISON_CARDS[0])
    with _gov() as gov:
        rb = RollbackManager(gov)
        rb.capture("pre-heist")
        verdict = evaluate_injection(
            gov,
            agent_id="external",
            kind="counterparty",
            name="meridian-bank-update",
            body={"instruction": text or card["text"]},
            source_trust_tier=card["tier"],
            evidence_ref=f"judge:{card_id}",
            simulate_chain_break=card.get("simulate_chain_break", False),
        )
    return TEMPLATES.TemplateResponse(
        "partials/verdict.html",
        {"request": request, "verdict": verdict.to_dict(), "card": card},
    )


@app.post("/rollback", response_class=HTMLResponse)
async def rollback(request: Request) -> HTMLResponse:
    with _gov() as gov:
        rb = RollbackManager(gov)
        result = rb.restore("pre-heist")
    return TEMPLATES.TemplateResponse(
        "partials/rollback.html",
        {"request": request, "result": result},
    )


@app.get("/congress", response_class=HTMLResponse)
async def congress(request: Request) -> HTMLResponse:
    with _gov() as gov:
        body = DisputeCongress(gov)
        w = gov.set_entity(
            "journal",
            "payout-status",
            {"status": "released"},
            agent_id="worker",
            evidence_ref="congress:vesper",
        )
        a = gov.set_entity(
            "journal",
            "payout-status-held",
            {"status": "held"},
            agent_id="auditor",
            evidence_ref="congress:kestrel",
        )
        tree_w = w.get("chain_entry", {}).get("tree", "")
        tree_a = a.get("chain_entry", {}).get("tree", "")
        dispute = body.open_dispute(
            dispute_id="CASE-2214-01",
            subject_category="worker:journal",
            subject_name="payout-status",
            version_a={"status": "released"},
            version_b={"status": "held"},
            agent_a="worker",
            agent_b="auditor",
            hash_a=w.get("content_hash", ""),
            hash_b=a.get("content_hash", ""),
        )
        citations = [{"tree": tree_a or tree_w}] if (tree_a or tree_w) else []
        dispute, arbiter_meta = body.arbitrate_with_vertex(
            dispute,
            citations=citations,
            fallback_winner_idx=1,
            confidence=0.92,
        )
        dispute = body.await_human_gate(dispute, approved=True)
        body.promote_resolution(dispute, subject_kind="journal", agent_id="worker")
    return TEMPLATES.TemplateResponse(
        "partials/congress.html",
        {"request": request, "dispute": dispute.to_body(), "arbiter": arbiter_meta},
    )


@app.get("/settlement", response_class=HTMLResponse)
async def settlement(request: Request) -> HTMLResponse:
    with _gov() as gov:
        data = write_receipts_to_governance(gov)
        context = build_decision_context(gov)
        decision = select_vendor(context)
        telemetry = TelemetryLogger(gov)
        cp = context.get("counterparty") or {}
        citations = [
            telemetry.build_citation("counterparty:meridian", cp),
        ]
        entry = telemetry.log_decision(
            agent="governance",
            citations=citations,
            outcome=decision,
            ts=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        telemetry.save_manifest(run_id=_commit_hash(), versions={"ledgermind": "0.1.0"})
        flip = telemetry.counterfactual_replay(select_vendor, context, remove_key="counterparty")
    return TEMPLATES.TemplateResponse(
        "partials/settlement.html",
        {
            "request": request,
            "data": data,
            "decision": decision,
            "flip": flip,
            "entry": entry.to_dict(),
        },
    )


@app.get("/waitlist/count")
async def waitlist_count() -> JSONResponse:
    return JSONResponse({"count": _waitlist_count})


@app.post("/waitlist")
async def waitlist_join() -> JSONResponse:
    global _waitlist_count
    _waitlist_count += 1
    return JSONResponse({"count": _waitlist_count})


@app.get("/montage", response_class=HTMLResponse)
async def montage(request: Request) -> HTMLResponse:
    with _gov() as gov:
        before = snapshot_entities(gov.raw.list_entities())
        gov.set_entity(
            "case",
            "CASE-2214",
            {"status": "resolved", "invoice": "INV-8841"},
            agent_id="planner",
            evidence_ref="montage:tier-promotion",
        )
        after = snapshot_entities(gov.raw.list_entities())
        diff = diff_snapshots(before, after)
        table = render_rich_table(diff)
    return TEMPLATES.TemplateResponse(
        "partials/montage.html",
        {"request": request, "diff": diff, "table": table},
    )


@app.get("/diff", response_class=HTMLResponse)
async def memory_diff(request: Request) -> HTMLResponse:
    with _gov() as gov:
        entities = gov.raw.list_entities()
        snap = snapshot_entities(entities)
    return TEMPLATES.TemplateResponse(
        "partials/montage.html",
        {"request": request, "diff": {"snapshot": snap}, "table": f"{len(snap)} entities indexed"},
    )
