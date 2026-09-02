"""Vertex AI Gemini bindings — google-genai + ChatVertexAI."""

from __future__ import annotations

import os
from functools import lru_cache

from google import genai
from google.genai import types
from langchain_google_vertexai import ChatVertexAI

from ledgermind.config import get_settings


def _project() -> str:
    settings = get_settings()
    return settings.google_cloud_project or os.environ.get("GOOGLE_CLOUD_PROJECT", "")


@lru_cache(maxsize=1)
def genai_client() -> genai.Client:
    project = _project()
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for Vertex AI")
    settings = get_settings()
    return genai.Client(vertexai=True, project=project, location=settings.vertex_location)


def _extract_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
            elif hasattr(block, "text"):
                parts.append(str(block.text))
            else:
                parts.append(str(block))
        return " ".join(parts)
    return str(content)


def chat_vertex(model: str | None = None, *, thinking_high: bool = False) -> ChatVertexAI:
    settings = get_settings()
    kwargs: dict = {
        "model": model or settings.model_planner,
        "project": _project(),
        "location": settings.vertex_location,
        "temperature": 0.2,
    }
    return ChatVertexAI(**kwargs)


def generate_content(model: str, prompt: str, *, thinking_high: bool = False) -> str:
    client = genai_client()
    config_kwargs: dict = {"temperature": 0.2}
    if thinking_high:
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level="HIGH")
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    return (response.text or "").strip()


def chat_invoke(model: str, prompt: str) -> str:
    llm = chat_vertex(model)
    out = llm.invoke(prompt)
    return _extract_text(getattr(out, "content", out))


def smoke_test() -> dict:
    settings = get_settings()
    prompt = "Reply with exactly: ledgermind-ok"
    text = generate_content(settings.model_smoke, prompt)
    chat_text = chat_invoke(settings.model_worker, "Reply with exactly: ledgermind-chat-ok")
    return {
        "ok": "ok" in text.lower() and "ok" in chat_text.lower(),
        "model_smoke": settings.model_smoke,
        "model_worker": settings.model_worker,
        "location": settings.vertex_location,
        "project": _project(),
        "genai_preview": text[:200],
        "chat_preview": chat_text[:200],
    }
