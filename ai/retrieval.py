# ai/retrieval.py
from __future__ import annotations

from storage.queries import (
    search_chunks,          # keyword
    search_chunks_vector,   # vector (expects qvec string "[...]" or returns [])
    list_chunks_for_doc,
    list_recent_chunks,
)


def retrieve_context(question: str, doc_id: str | None, top_k: int = 5) -> list[dict]:
    """
    Retrieve top-k relevant chunks.

    Order:
    1) Vector search (if query is a vector literal "[...]" OR vector search is enabled upstream)
    2) Keyword search
    3) Fallback:
        - if doc_id: first chunks from that document
        - else: most recent chunks overall
    """
    top_k = max(1, min(int(top_k or 5), 20))
    q = (question or "").strip()

    results = []

    # 1) Vector search first (only works if q is already a vector literal)
    if q:
        try:
            results = search_chunks_vector(q=q, doc_id=doc_id, limit=top_k, offset=0) or []
        except Exception:
            results = []

    # 2) Keyword fallback
    if not results and q:
        results = search_chunks(q=q, doc_id=doc_id, limit=top_k, offset=0) or []

    # 3) Guaranteed fallback
    if not results:
        if doc_id:
            rows = list_chunks_for_doc(doc_id, limit=top_k, offset=0) or []
        else:
            rows = list_recent_chunks(limit=top_k) or []

        results = []
        for r in rows:
            content = (r.get("content") or "").strip()
            results.append(
                {
                    "chunk_id": str(r.get("chunk_id") or r["id"]),
                    "document_id": str(r["document_id"]),
                    "filename": r.get("filename"),
                    "chunk_index": int(r.get("chunk_index") or 0),
                    "score": float(r.get("score") or 0.0),
                    "preview": (content[:300] + "…") if len(content) > 300 else content,
                }
            )

    return results
