"""FastAPI app: JSON API for the Next.js front end, plus a Jinja fallback UI.

Both surfaces read the same functions in ui/api.py, so they cannot disagree about what
the demo did. The Jinja routes are the fallback: if the Next.js app is not running, the
demo still boots and every beat still renders.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from ledgermind.config import get_settings
from ledgermind.store import GovernedMemoryClient

from ui import api

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

app = FastAPI(title="Ledgermind Demo", version="0.1.0")

# The front end is a local demo surface, so accept it from any loopback or private-LAN
# origin rather than one hardcoded port. Pinning :3000 meant the app silently rendered an
# empty page on any other port -- every fetch blocked by CORS with no visible error -- and
# `next start` advertises a LAN address (192.168.x.x) that would have failed the same way.
# LEDGERMIND_CORS_ORIGINS overrides with an explicit comma-separated list when needed.
_LOCAL_ORIGIN = re.compile(
    r"^https?://("
    r"localhost"
    r"|127\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|\[::1\]"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r")(:\d+)?$"
)

_explicit = [o.strip() for o in os.environ.get("LEDGERMIND_CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_explicit or [],
    allow_origin_regex=None if _explicit else _LOCAL_ORIGIN.pattern,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

_waitlist_count = 0


def _gov() -> GovernedMemoryClient:
    return GovernedMemoryClient(get_settings().sibyl_memory_db)


def _with_gov(fn: Callable[..., dict[str, Any]], *args: Any) -> dict[str, Any]:
    with _gov() as gov:
        return fn(gov, *args)


# --------------------------------------------------------------------------- JSON API


@app.get("/api/state")
async def api_state() -> JSONResponse:
    return JSONResponse(_with_gov(api.state_data))


@app.post("/api/inject")
async def api_inject(payload: dict[str, Any]) -> JSONResponse:
    card_id = str(payload.get("card_id", ""))
    text = str(payload.get("text", ""))
    return JSONResponse(_with_gov(api.inject_data, card_id, text))


@app.post("/api/rollback")
async def api_rollback() -> JSONResponse:
    return JSONResponse(_with_gov(api.rollback_data))


@app.get("/api/congress")
async def api_congress() -> JSONResponse:
    return JSONResponse(_with_gov(api.congress_data))


@app.get("/api/settlement")
async def api_settlement() -> JSONResponse:
    return JSONResponse(_with_gov(api.settlement_data))


@app.get("/api/montage")
async def api_montage() -> JSONResponse:
    return JSONResponse(_with_gov(api.montage_data))


@app.get("/api/diff")
async def api_diff() -> JSONResponse:
    return JSONResponse(_with_gov(api.diff_data))


@app.get("/api/recall")
async def api_recall() -> JSONResponse:
    """Fresh-session recall beat — the rules section 03 gate evidence."""
    return JSONResponse(_with_gov(api.recall_data))


# ------------------------------------------------------------------ Jinja fallback UI


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {
            "commit": api.commit_hash(),
            "timestamp": api.utc_now(),
            "poison_cards": api.POISON_CARDS,
        },
    )


@app.post("/inject", response_class=HTMLResponse)
async def inject(request: Request, card_id: str = Form(...), text: str = Form("")) -> HTMLResponse:
    data = _with_gov(api.inject_data, card_id, text)
    return TEMPLATES.TemplateResponse(
        request, "partials/verdict.html", {"verdict": data["verdict"], "card": data["card"]}
    )


@app.post("/rollback", response_class=HTMLResponse)
async def rollback(request: Request) -> HTMLResponse:
    data = _with_gov(api.rollback_data)
    return TEMPLATES.TemplateResponse(request, "partials/rollback.html", {"result": data["result"]})


@app.get("/congress", response_class=HTMLResponse)
async def congress(request: Request) -> HTMLResponse:
    data = _with_gov(api.congress_data)
    return TEMPLATES.TemplateResponse(
        request, "partials/congress.html", {"dispute": data["dispute"], "arbiter": data["arbiter"]}
    )


@app.get("/settlement", response_class=HTMLResponse)
async def settlement(request: Request) -> HTMLResponse:
    data = _with_gov(api.settlement_data)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/settlement.html",
        {
            "data": {k: data[k] for k in ("receipts", "unexercised_stacks") if k in data},
            "decision": data["decision"],
            "flip": data["flip"],
            "entry": data["entry"],
        },
    )


@app.get("/montage", response_class=HTMLResponse)
async def montage(request: Request) -> HTMLResponse:
    data = _with_gov(api.montage_data)
    return TEMPLATES.TemplateResponse(
        request, "partials/montage.html", {"diff": data["diff"], "table": data["table"]}
    )


@app.get("/diff", response_class=HTMLResponse)
async def memory_diff(request: Request) -> HTMLResponse:
    data = _with_gov(api.diff_data)
    return TEMPLATES.TemplateResponse(
        request, "partials/montage.html", {"diff": data["diff"], "table": data["table"]}
    )


@app.get("/waitlist/count")
async def waitlist_count() -> JSONResponse:
    return JSONResponse({"count": _waitlist_count})


@app.post("/waitlist")
async def waitlist_join() -> JSONResponse:
    global _waitlist_count
    _waitlist_count += 1
    return JSONResponse({"count": _waitlist_count})
