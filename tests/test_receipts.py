"""Live receipt validation tests."""

from __future__ import annotations

from onchain.receipts import is_live_receipt, is_live_tx_hash


def test_rejects_fake_tx_hashes():
    assert not is_live_tx_hash("0x" + "a" * 64)
    assert not is_live_tx_hash("0x" + "b" * 64)
    assert is_live_tx_hash("0xc85049e1927f79c565b61a8ab7c824aa7ffb10b2e07b30deb067f6745416005a")


def test_rejects_test_fixture_source():
    assert not is_live_receipt({"kind": "x402", "tx_hash": "0x" + "a" * 64, "source": "test-fixture"})


def test_accepts_live_x402():
    assert is_live_receipt(
        {
            "kind": "x402",
            "tx_hash": "0xc85049e1927f79c565b61a8ab7c824aa7ffb10b2e07b30deb067f6745416005a",
            "source": "live",
        }
    )
