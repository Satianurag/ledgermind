"""Integration tests for live onchain reads."""

from __future__ import annotations

import pytest

from onchain.b20 import read_b20


@pytest.mark.integration
def test_b20_live_read():
    import os

    os.environ["B20_RPC_URL"] = "https://mainnet.base.org"
    result = read_b20()
    assert result["source"] == "live"
    assert "balanceOf" in result
    assert "multiplier" in result
    assert result["activated"] is True
