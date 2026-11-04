# storage/vector_search.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy import text
from storage.db import engine


def vector_search_chunks(
    query_vec: List[float],
    doc_id: Optional[str] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    vec = "[" + ",".join(str(float(x)) for x in query_vec) + "]"

    sql = """
        SELECT
            id AS chunk_id,
            document_id,
            chunk_index,
            content,
            1 - (embedding <=> :qvec::vector) AS score
        FROM chunks
        WHERE embedding IS NOT NULL
    """
    params: Dict[str, Any] = {"qvec": vec, "top_k": top_k}

    if doc_id:
        sql += " AND document_id = :doc_id::uuid"
        params["doc_id"] = doc_id

    sql += " ORDER BY embedding <=> :qvec::vector LIMIT :top_k"

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return [dict(r) for r in rows]
