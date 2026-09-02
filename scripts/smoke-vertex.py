"""Smoke test for Vertex AI global endpoint (PRD §6.13 V6/V15)."""

from __future__ import annotations

import json
import sys

from ledgermind.config import get_settings
from ledgermind.vertex import smoke_test


def main() -> int:
    settings = get_settings()
    if not settings.google_cloud_project and not __import__("os").environ.get("GOOGLE_CLOUD_PROJECT"):
        print(json.dumps({"ok": False, "error": "GOOGLE_CLOUD_PROJECT not set"}))
        return 1

    results = smoke_test()
    print(json.dumps(results, indent=2))
    return 0 if results.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
