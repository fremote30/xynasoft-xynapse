# storage/queries.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy import text
from storage.db import engine


# -------------------------
# Documents
# -------------------------

def list_documents(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    sql = """
        SELECT id, filename, sha256, content_type, created_at,
               COALESCE(length(raw_text), 0) AS chars
        FROM documents
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"limit": limit, "offset": offset}).mappings().all()
    return [dict(r) for r in rows]


def get_document_stats(doc_id: str) -> Optional[Dict[str, Any]]:
    sql = """
        SELECT d.id, d.filename, d.sha256, d.created_at,
               COALESCE(length(d.raw_text), 0) AS chars,
               COALESCE(c.cnt, 0) AS chunks
        FROM documents d
        LEFT JOIN (
            SELECT document_id, COUNT(*) AS cnt
            FROM chunks
            WHERE document_id = :doc_id::uuid
            GROUP BY document_id
        ) c ON c.document_id = d.id
        WHERE d.id = :doc_id::uuid
        LIMIT 1
    """
    with engine.connect() as conn:
        row = conn.execute(text(sql), {"doc_id": doc_id}).mappings().first()
    return dict(row) if row else None


# -------------------------
# Chunks: insert/list
# -------------------------

def insert_chunks(document_id: str, chunks: List[str]) -> int:
    if not chunks:
        return 0

    sql = """
        INSERT INTO chunks (id, document_id, chunk_index, content)
        VALUES (gen_random_uuid(), :doc_id::uuid, :chunk_index, :content)
    """

    with engine.begin() as conn:
        for i, content in enumerate(chunks):
            conn.execute(
                text(sql),
                {"doc_id": document_id, "chunk_index": i, "content": content},
            )

    return len(chunks)


def list_chunks_for_doc(doc_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    sql = """
        SELECT id, document_id, chunk_index, content, created_at,
               NULL::float8 AS score,
               NULL::text AS filename
        FROM chunks
        WHERE document_id = :doc_id::uuid
        ORDER BY chunk_index ASC
        LIMIT :limit OFFSET :offset
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text(sql),
            {"doc_id": doc_id, "limit": limit, "offset": offset},
        ).mappings().all()
    return [dict(r) for r in rows]


def list_recent_chunks(limit: int = 10) -> List[Dict[str, Any]]:
    sql = """
        SELECT c.id, c.document_id, c.chunk_index, c.content, c.created_at,
               NULL::float8 AS score,
               d.filename AS filename
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        ORDER BY c.created_at DESC
        LIMIT :limit
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"limit": limit}).mappings().all()
    return [dict(r) for r in rows]


# -------------------------
# Keyword search (simple ILIKE)
# -------------------------

def search_chunks(q: str, doc_id: str | None = None, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    # simple + safe keyword search (works without pg_trgm)
    sql = """
        SELECT c.id AS chunk_id,
               c.document_id,
               d.filename AS filename,
               c.chunk_index,
               0.0::float8 AS score,
               CASE
                 WHEN length(c.content) > 300 THEN substring(c.content from 1 for 300) || '…'
                 ELSE c.content
               END AS preview
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.content ILIKE :pattern
    """
    params: Dict[str, Any] = {
        "pattern": f"%{q.strip()}%",
        "limit": limit,
        "offset": offset,
    }

    if doc_id:
        sql += " AND c.document_id = :doc_id::uuid"
        params["doc_id"] = doc_id

    sql += """
        ORDER BY c.created_at DESC
        LIMIT :limit OFFSET :offset
    """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return [dict(r) for r in rows]


# -------------------------
# Vector search (pgvector cosine distance)
# Requires: chunks.embedding vector(1536) populated
# -------------------------

def search_chunks_vector(q: str, doc_id: str | None, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Vector search over chunks.embedding using cosine distance.
    This function returns [] if it can't run (e.g., no embeddings yet).
    You must pass an embedding string for q elsewhere OR use a local embedder.
    In this project, we assume ai.embeddings.embed_texts() is called upstream,
    and this function is used with a precomputed query vector.

    To keep your API simple, we'll support both:
      - if q already looks like a pgvector literal "[...]" we use it directly
      - otherwise return [] (so retrieval falls back to keyword)
    """
    qs = (q or "").strip()
    if not (qs.startswith("[") and qs.endswith("]")):
        # No query embedding available in this function; fall back safely.
        return []

    sql = """
        SELECT c.id AS chunk_id,
               c.document_id,
               d.filename AS filename,
               c.chunk_index,
               (1 - (c.embedding <=> :qvec::vector))::float8 AS score,
               CASE
                 WHEN length(c.content) > 300 THEN substring(c.content from 1 for 300) || '…'
                 ELSE c.content
               END AS preview
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
    """

    params: Dict[str, Any] = {"qvec": qs, "limit": limit, "offset": offset}

    if doc_id:
        sql += " AND c.document_id = :doc_id::uuid"
        params["doc_id"] = doc_id

    sql += """
        ORDER BY c.embedding <=> :qvec::vector ASC
        LIMIT :limit OFFSET :offset
    """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return [dict(r) for r in rows]


# -------------------------
# Embedding status helper
# -------------------------

def count_unembedded_chunks(doc_id: str | None = None) -> int:
    sql = "SELECT COUNT(*) FROM chunks WHERE embedding IS NULL"
    params: Dict[str, Any] = {}
    if doc_id:
        sql += " AND document_id = :doc_id::uuid"
        params["doc_id"] = doc_id

    with engine.connect() as conn:
        return int(conn.execute(text(sql), params).scalar() or 0)
