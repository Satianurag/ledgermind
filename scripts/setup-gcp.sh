#!/usr/bin/env bash
# Day-1 GCP + Vertex setup (PRD §6.13)
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-}"
if [[ -z "$PROJECT" ]]; then
  PROJECT=$(gcloud config get-value project 2>/dev/null || true)
fi
if [[ -z "$PROJECT" ]]; then
  echo "Set GOOGLE_CLOUD_PROJECT or run: gcloud config set project YOUR_PROJECT"
  exit 1
fi

echo "Project: $PROJECT"
gcloud services enable aiplatform.googleapis.com --project="$PROJECT"
gcloud auth application-default print-access-token >/dev/null 2>&1 || \
  gcloud auth application-default login

echo "Gemini models (global):"
gcloud ai models list --region=global --project="$PROJECT" \
  --filter='displayName~gemini' --format='table(name,versionId)' 2>/dev/null | head -20 || \
  echo "(model list requires Vertex API access)"

echo "Pin conflict check (expected ResolutionImpossible):"
pip install --dry-run "langgraph==1.2.11" "sibyl-memory-langgraph==0.1.1" 2>&1 | tail -3 || true

export GOOGLE_CLOUD_PROJECT="$PROJECT"
export VERTEX_LOCATION=global
uv run python scripts/smoke-vertex.py
