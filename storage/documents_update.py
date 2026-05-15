from __future__ import annotations

from sqlalchemy import text
from storage.db import engine


def update_document_text(doc_id: str, raw_text: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE documents
                SET raw_text = :raw_text
                WHERE id = :id::uuid
            """),
            {"id": doc_id, "raw_text": raw_text},
        )


def delete_chunks_for_doc(doc_id: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM chunks WHERE document_id = :id::uuid"),
            {"id": doc_id},
        )
