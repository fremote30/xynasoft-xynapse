# ai/embeddings.py
from __future__ import annotations

import os
from typing import List

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


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Returns list of embedding vectors.
    """
    if not texts:
        return []

    client = _get_client()
    model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    response = client.embeddings.create(
        model=model,
        input=texts,
    )

    return [d.embedding for d in response.data]
