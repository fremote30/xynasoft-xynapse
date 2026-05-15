# storage/embeddings.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any

from sqlalchemy import text
from storage.db import engine


def fetch_unembedded_chunks(limit: int = 50, doc_id: str | None = None) -> List[Dict[str, Any]]:
    sql = """
        SELECT id, document_id, chunk_index, content
        FROM chunks
        WHERE embedding IS NULL
    """
    params: Dict[str, Any] = {"limit": int(limit)}

    if doc_id:
        sql += " AND document_id = CAST(:doc_id AS uuid)"
        params["doc_id"] = doc_id

    sql += " ORDER BY created_at ASC LIMIT :limit"

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return [dict(r) for r in rows]


def update_chunk_embedding(chunk_id: str, embedding: List[float]) -> None:
    # pgvector accepts: '[0.1,0.2,...]'
    vec = "[" + ",".join(f"{float(x)}" for x in embedding) + "]"
    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE chunks
                SET embedding = CAST(:vec AS vector),
                    embedded_at = :now
                WHERE id = CAST(:chunk_id AS uuid)
            """),
            {"vec": vec, "now": now, "chunk_id": chunk_id},
        )
