from __future__ import annotations
import uuid
from uuid import uuid4
from sqlalchemy import text
from storage.db import engine
from typing import Optional

def insert_document(filename: str,sha256: str,raw_text: str,content_type: Optional[str] = None,
    bytes_data: Optional[bytes] = None,) -> uuid.UUID:
    doc_id = uuid.uuid4()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO documents (id, filename, sha256, raw_text, content_type, bytes, bytes_size)
                VALUES (:id, :filename, :sha256, :raw_text, :content_type, :bytes, :bytes_size)
                """
            ),
            {
                "id": str(doc_id),
                "filename": filename,
                "sha256": sha256,
                "raw_text": raw_text,
                "content_type": content_type,
                "bytes": bytes_data,
                "bytes_size": len(bytes_data) if bytes_data else None,
            },
        )

    return doc_id


def upsert_document_blob(document_id: str, content_type: str, data: bytes) -> None:
    """Insert or replace the bytes for a document."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO document_blobs (document_id, content_type, bytes, size_bytes)
                VALUES (:document_id, :content_type, :bytes, :size_bytes)
                ON CONFLICT (document_id)
                DO UPDATE SET
                    content_type = EXCLUDED.content_type,
                    bytes = EXCLUDED.bytes,
                    size_bytes = EXCLUDED.size_bytes
                """
            ),
            {
                "document_id": document_id,
                "content_type": content_type or "application/octet-stream",
                "bytes": data,
                "size_bytes": int(len(data)),
            },
        )


def get_document_blob_bytes(document_id: str) -> bytes | None:
    """Fetch raw bytes for a document, if stored."""
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT bytes
                FROM document_blobs
                WHERE document_id = :document_id
                """
            ),
            {"document_id": document_id},
        ).fetchone()
    return row[0] if row else None


def update_document_raw_text(document_id: str, raw_text: str) -> None:
    """Update raw_text after OCR."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE documents
                SET raw_text = :raw_text
                WHERE id = :document_id
                """
            ),
            {"document_id": document_id, "raw_text": raw_text},
        )
