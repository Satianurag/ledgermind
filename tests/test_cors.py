"""CORS must not be pinned to one port.

The front end is a local demo surface. Pinning http://localhost:3000 meant the app
rendered an empty page on any other port -- every fetch blocked, no visible error -- and
`next start` advertises a LAN address that failed the same way. A judge running the demo
on a different port would have seen a blank console.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ui.app import app

client = TestClient(app)


def _preflight(origin: str):
    return client.options(
        "/api/state",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:3000",
        "http://localhost:3901",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://192.168.0.111:3000",
        "http://10.0.0.5:3901",
    ],
)
def test_local_origins_are_allowed_on_any_port(origin):
    response = _preflight(origin)
    assert response.status_code == 200, origin
    assert response.headers.get("access-control-allow-origin") == origin


@pytest.mark.parametrize(
    "origin",
    ["https://evil.example.com", "http://ledgermind.attacker.io"],
)
def test_public_origins_are_not_allowed(origin):
    response = _preflight(origin)
    assert response.headers.get("access-control-allow-origin") != origin
