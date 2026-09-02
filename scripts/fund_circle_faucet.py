"""Fund a Base Sepolia address via Circle web faucet (Playwright)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def fund_via_circle(address: str, timeout_s: int = 120) -> dict:
    from playwright.sync_api import sync_playwright

    result: dict = {"ok": False, "address": address, "source": "circle_faucet_web"}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://faucet.circle.com/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

        # Select Base Sepolia network if dropdown present
        for label in ("Base Sepolia", "BASE-SEPOLIA", "Base"):
            try:
                page.get_by_text(label, exact=False).first.click(timeout=3000)
                break
            except Exception:
                continue

        # Address input
        filled = False
        for selector in (
            'input[placeholder*="address" i]',
            'input[name="address"]',
            'input[type="text"]',
        ):
            try:
                loc = page.locator(selector).first
                if loc.count():
                    loc.fill(address)
                    filled = True
                    break
            except Exception:
                continue
        if not filled:
            result["error"] = "could not find address input on Circle faucet"
            browser.close()
            return result

        # Submit
        clicked = False
        for text in ("Send 20 USDC", "Send USDC", "Send"):
            try:
                page.get_by_role("button", name=text).first.click(timeout=5000)
                clicked = True
                break
            except Exception:
                continue
        if not clicked:
            result["error"] = "could not find submit button on Circle faucet"
            browser.close()
            return result

        deadline = time.time() + timeout_s
        while time.time() < deadline:
            body = page.content().lower()
            if any(
                token in body
                for token in (
                    "success",
                    "sent",
                    "transaction",
                    "funded",
                    "limit exceeded",
                    "too many",
                )
            ):
                result["ok"] = "limit" not in body and "too many" not in body
                result["page_hint"] = body[:500]
                break
            page.wait_for_timeout(2000)
        browser.close()
    return result


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/fund_circle_faucet.py <0xaddress>")
        return 1
    out = fund_via_circle(sys.argv[1])
    print(out)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
