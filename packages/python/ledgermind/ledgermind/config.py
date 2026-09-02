"""Application settings from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    google_cloud_project: str
    vertex_location: str
    model_planner: str
    model_worker: str
    model_auditor: str
    model_arbiter: str
    model_smoke: str
    sibyl_memory_db: str
    human_gate_threshold: float
    wallet_cap_usdc: float
    onchain_network: str

    @classmethod
    def from_env(cls) -> Settings:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        return cls(
            google_cloud_project=project,
            vertex_location=os.environ.get("VERTEX_LOCATION", "global"),
            model_planner=os.environ.get("MODEL_PLANNER", "gemini-3.1-pro-preview"),
            model_worker=os.environ.get("MODEL_WORKER", "gemini-3.5-flash"),
            model_auditor=os.environ.get("MODEL_AUDITOR", "gemini-3.1-pro-preview"),
            model_arbiter=os.environ.get("MODEL_ARBITER", "gemini-3.1-pro-preview"),
            model_smoke=os.environ.get("MODEL_SMOKE", "gemini-3.1-flash-lite"),
            sibyl_memory_db=os.environ.get("SIBYL_MEMORY_DB", "demo-data/memory.db"),
            human_gate_threshold=float(os.environ.get("HUMAN_GATE_CONFIDENCE_THRESHOLD", "0.85")),
            wallet_cap_usdc=float(os.environ.get("WALLET_CAP_USDC", "2.00")),
            onchain_network=os.environ.get("ONCHAIN_NETWORK", "base-sepolia"),
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings
