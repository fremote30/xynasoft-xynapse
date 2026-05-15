# ai/llm.py
from __future__ import annotations

import os
from openai import OpenAI

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client:
        return _client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    _client = OpenAI(api_key=api_key)
    return _client


def ask_llm(prompt: str) -> str:
    client = _get_client()
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a precise legal and document analysis assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content.strip()
